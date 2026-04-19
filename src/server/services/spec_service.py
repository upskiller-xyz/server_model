import json
import re
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any

from ..interfaces import IDownloadStrategy, ILogger, ISpecService

_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ModelSpecService(ISpecService):
    """Fetches and caches model spec.json files.

    spec.json lives at spec_url_template.format(name=model_name) on S3
    and is cached locally at checkpoints_dir/{model_name}.json.
    """

    def __init__(
        self,
        checkpoints_dir: str,
        download_strategy: IDownloadStrategy,
        logger: ILogger,
        spec_url_template: str,
    ):
        if "{name}" not in spec_url_template:
            raise ValueError(
                f"SPEC_URL_TEMPLATE must contain '{{name}}' placeholder, got: {spec_url_template!r}"
            )
        try:
            spec_url_template.format(name="__validation__")
        except (KeyError, ValueError) as e:
            raise ValueError(f"SPEC_URL_TEMPLATE is not a valid format string: {e}") from e

        self._checkpoints_dir = Path(checkpoints_dir)
        self._download_strategy = download_strategy
        self._logger = logger
        self._spec_url_template = spec_url_template
        self._lock = threading.Lock()

    def _validate_model_name(self, model_name: str) -> None:
        if not _MODEL_NAME_RE.match(model_name):
            raise ValueError(f"Invalid model name: '{model_name}'")
        resolved = (self._checkpoints_dir / f"{model_name}.json").resolve()
        if not resolved.is_relative_to(self._checkpoints_dir.resolve()):
            raise ValueError(f"Model name escapes checkpoints directory: '{model_name}'")

    def get_spec(self, model_name: str) -> Dict[str, Any]:
        """Return spec dict for model_name, downloading if not cached locally."""
        self._validate_model_name(model_name)
        local_path = self._checkpoints_dir / f"{model_name}.json"

        with self._lock:
            if not local_path.exists():
                url = self._spec_url_template.format(name=model_name)
                self._logger.info(f"Downloading spec for '{model_name}' from {url}")
                tmp_path = local_path.with_suffix(".json.tmp")
                try:
                    self._download_strategy.download(url, str(tmp_path))
                    tmp_path.replace(local_path)
                except Exception:
                    tmp_path.unlink(missing_ok=True)
                    raise

        with open(local_path) as f:
            return json.load(f)


class SpecServiceFactory:
    @staticmethod
    def create(
        checkpoints_dir: str,
        download_strategy: IDownloadStrategy,
        logger: ILogger,
        spec_url_template: str,
    ) -> ISpecService:
        return ModelSpecService(
            checkpoints_dir=checkpoints_dir,
            download_strategy=download_strategy,
            logger=logger,
            spec_url_template=spec_url_template,
        )
