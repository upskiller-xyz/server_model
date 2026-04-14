import os
from pathlib import Path
import requests
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from ..interfaces import IDownloadStrategy, ILogger


class HTTPDownloadStrategy(IDownloadStrategy):
    """HTTP-based download strategy"""

    def __init__(self, logger: ILogger, chunk_size: int = 8192):
        self._logger = logger
        self._chunk_size = chunk_size

    def download(self, url: str, local_path: str) -> str:
        """Download file from HTTP URL to local path"""
        if os.path.exists(local_path):
            self._logger.info(f"File already exists at {local_path}")
            return local_path

        self._logger.info(f"Downloading from {url} to {local_path}")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            with open(local_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=self._chunk_size):
                    if chunk:
                        file.write(chunk)

            self._logger.info(f"Download completed: {local_path}")
            return local_path

        except requests.RequestException as e:
            self._logger.error(f"Download failed: {str(e)}")
            raise
        except IOError as e:
            self._logger.error(f"File write failed: {str(e)}")
            raise


class S3DownloadStrategy(IDownloadStrategy):
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
    ):
        self._logger = logger
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def download(self, url: str, local_path: str) -> str:
        """Download file from private S3 bucket to local path.

        Args:
            url: S3 URL in s3://bucket/key format
            local_path: Destination path on disk

        Returns:
            local_path after successful download
        """
        if os.path.exists(local_path):
            self._logger.info(f"File already exists at {local_path}")
            return local_path

        if not url.startswith("s3://"):
            raise ValueError(f"Invalid S3 URL — expected s3://bucket/key, got: {url!r}")
        without_scheme = url[len("s3://"):]
        parts = without_scheme.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid S3 URL — expected s3://bucket/key, got: {url!r}")
        bucket, key = parts

        self._logger.info(f"Downloading s3://{bucket}/{key} to {local_path}")

        try:
            parent = Path(local_path).parent
            if parent != Path("."):
                parent.mkdir(parents=True, exist_ok=True)
            self._s3.download_file(bucket, key, local_path)
            self._logger.info(f"Download completed: {local_path}")
            return local_path
        except (ClientError, BotoCoreError) as e:
            self._logger.error(f"S3 download failed: {str(e)}")
            raise
        except OSError as e:
            self._logger.error(f"File write failed: {str(e)}")
            raise