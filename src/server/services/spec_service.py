import json
from pathlib import Path
from typing import Dict, Any

from ..interfaces import IDownloadStrategy, ILogger, ISpecService


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
        self._checkpoints_dir = Path(checkpoints_dir)
        self._download_strategy = download_strategy
        self._logger = logger
        self._spec_url_template = spec_url_template

    def get_spec(self, model_name: str) -> Dict[str, Any]:
        """Return spec dict for model_name, downloading if not cached locally."""
        local_path = self._checkpoints_dir / f"{model_name}.json"

        if not local_path.exists():
            url = self._spec_url_template.format(name=model_name)
            self._logger.info(f"Downloading spec for '{model_name}' from {url}")
            self._download_strategy.download(url, str(local_path))

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
