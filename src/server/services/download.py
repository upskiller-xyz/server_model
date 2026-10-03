import hashlib
import hmac
import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Mapping, Optional
import requests
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from ..interfaces import IDownloadStrategy, ILogger


class ArtifactIntegrityError(Exception):
    """Raised when a downloaded artifact fails checksum verification."""


class IArtifactVerifier(ABC):
    """Verifies a downloaded artifact before it is moved into the cache."""

    @abstractmethod
    def precheck(self, file_name: str) -> None:
        """Raise before any transfer if ``file_name`` may not be downloaded."""

    @abstractmethod
    def verify(self, file_name: str, path: str) -> None:
        """Raise ``ArtifactIntegrityError`` if the file at ``path`` is not trusted."""


class AtomicDownloadStrategy(IDownloadStrategy):
    """Template method: fetch into a temp file, verify, then atomically move into place.

    A failed, interrupted or unverified transfer never leaves a file at
    ``local_path`` (the cache check would otherwise reuse it on every later request).
    """

    def __init__(self, logger: ILogger, verifier: Optional[IArtifactVerifier] = None):
        self._logger = logger
        self._verifier = verifier

    def download(self, url: str, local_path: str) -> str:
        file_name = Path(local_path).name
        if os.path.exists(local_path) and self._accept_cached(file_name, local_path):
            self._logger.info(f"File already exists at {local_path}")
            return local_path

        if self._verifier is not None:
            self._verifier.precheck(file_name)

        parent = Path(local_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".download-", suffix=".part")
        os.close(fd)
        try:
            self._fetch(url, tmp_path)
            if self._verifier is not None:
                self._verifier.verify(file_name, tmp_path)
            os.replace(tmp_path, local_path)
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

        self._logger.info(f"Download completed: {local_path}")
        return local_path

    def _accept_cached(self, file_name: str, local_path: str) -> bool:
        """Whether the file already at ``local_path`` may be used as it is.

        The cached artifact goes through the same gate as a fresh transfer:
        ``precheck`` first, so a required registry refuses an unpinned file
        instead of trusting whatever happens to be on disk, then the digest.
        A pinned file that no longer matches is dropped and refetched, so a
        stale or tampered artifact is never loaded just because it exists.
        """
        if self._verifier is None:
            return True
        self._verifier.precheck(file_name)
        try:
            self._verifier.verify(file_name, local_path)
            return True
        except ArtifactIntegrityError:
            self._logger.warning(
                f"Cached '{local_path}' failed SHA-256 verification — refetching"
            )
            Path(local_path).unlink(missing_ok=True)
            return False

    @abstractmethod
    def _fetch(self, url: str, tmp_path: str) -> None:
        """Write the artifact at ``url`` to ``tmp_path``."""


class HTTPDownloadStrategy(AtomicDownloadStrategy):
    """HTTP-based download strategy"""

    def __init__(
        self,
        logger: ILogger,
        chunk_size: int = 8192,
        timeout: tuple[float, float] = (10.0, 300.0),
        verifier: Optional[IArtifactVerifier] = None,
    ):
        super().__init__(logger, verifier)
        self._chunk_size = chunk_size
        self._timeout = timeout

    def _fetch(self, url: str, tmp_path: str) -> None:
        self._logger.info(f"Downloading from {url}")
        try:
            with requests.get(url, stream=True, timeout=self._timeout) as response:
                response.raise_for_status()
                with open(tmp_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=self._chunk_size):
                        if chunk:
                            file.write(chunk)
        except requests.RequestException as e:
            self._logger.error(f"Download failed: {str(e)}")
            raise
        except IOError as e:
            self._logger.error(f"File write failed: {str(e)}")
            raise


class S3DownloadStrategy(AtomicDownloadStrategy):
    """Scaleway S3 download strategy for private buckets.

    Expects URLs in s3://bucket/key format.
    Uses boto3 with Scaleway's S3-compatible endpoint.
    """

    def __init__(
        self,
        logger: ILogger,
        access_key: str,
        secret_key: str,
        region: str,
        endpoint_url: str,
        verifier: Optional[IArtifactVerifier] = None,
    ):
        super().__init__(logger, verifier)
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    @staticmethod
    def _parse(url: str) -> tuple[str, str]:
        if not url.startswith("s3://"):
            raise ValueError(f"Invalid S3 URL — expected s3://bucket/key, got: {url!r}")
        parts = url[len("s3://"):].split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid S3 URL — expected s3://bucket/key, got: {url!r}")
        return parts[0], parts[1]

    def download(self, url: str, local_path: str) -> str:
        """Download file from private S3 bucket to local path.

        Args:
            url: S3 URL in s3://bucket/key format
            local_path: Destination path on disk

        Returns:
            local_path after successful download
        """
        self._parse(url)  # reject malformed URLs before touching the disk
        return super().download(url, local_path)

    def _fetch(self, url: str, tmp_path: str) -> None:
        bucket, key = self._parse(url)
        self._logger.info(f"Downloading s3://{bucket}/{key}")
        try:
            self._s3.download_file(bucket, key, tmp_path)
        except (ClientError, BotoCoreError) as e:
            self._logger.error(f"S3 download failed: {str(e)}")
            raise
        except OSError as e:
            self._logger.error(f"File write failed: {str(e)}")
            raise


class ChecksumRegistry:
    """Pinned SHA-256 digests keyed by local artifact file name (e.g. ``df_default_2.0.1.onnx``)."""

    def __init__(self, digests: Mapping[str, str], required: bool = False):
        self._digests: Dict[str, str] = {name: digest.strip().lower() for name, digest in digests.items()}
        self._required = required

    @classmethod
    def from_json(cls, raw: Optional[str], required: bool = False) -> "ChecksumRegistry":
        """Parse a JSON object ``{"<file name>": "<sha256 hex>"}``; empty → no pins."""
        if raw is None or not raw.strip():
            return cls({}, required)
        parsed = json.loads(raw)
        if not isinstance(parsed, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()
        ):
            raise ValueError("Checksum pins must be a JSON object of file name → sha256 hex")
        return cls(parsed, required)

    @property
    def required(self) -> bool:
        return self._required

    def expected(self, file_name: str) -> Optional[str]:
        return self._digests.get(file_name)


class ChecksumVerifier(IArtifactVerifier):
    """SHA-256 verification against a ``ChecksumRegistry``.

    Pinned digest present → mismatch raises. No pin → allowed with a warning,
    unless the registry is ``required``.
    """

    _HASH_CHUNK = 1024 * 1024

    def __init__(self, registry: ChecksumRegistry, logger: ILogger):
        self._registry = registry
        self._logger = logger

    def precheck(self, file_name: str) -> None:
        if self._registry.required and self._registry.expected(file_name) is None:
            raise ArtifactIntegrityError(f"No pinned SHA-256 for '{file_name}'; refusing to download")

    def verify(self, file_name: str, path: str) -> None:
        expected = self._registry.expected(file_name)
        if expected is None:
            self._logger.warning(f"No pinned SHA-256 for '{file_name}'; integrity not verified")
            return
        actual = self._sha256(path)
        if not hmac.compare_digest(actual, expected):
            raise ArtifactIntegrityError(
                f"SHA-256 mismatch for '{file_name}': expected {expected}, got {actual}"
            )
        self._logger.info(f"SHA-256 verified for '{file_name}'")

    @classmethod
    def _sha256(cls, path: str) -> str:
        digest = hashlib.sha256()
        with open(path, 'rb') as file:
            for chunk in iter(lambda: file.read(cls._HASH_CHUNK), b''):
                digest.update(chunk)
        return digest.hexdigest()
