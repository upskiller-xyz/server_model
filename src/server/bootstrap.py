"""Shared dependency wiring for all server adapters (Flask, Modal, ...).

Builds the logger, download strategies, simulation/spec services and the
controller from environment variables. Both the Flask entry point (main.py)
and the Modal adapter (modal_app/) call ServerBootstrap.from_env() so the
wiring lives in exactly one place.
"""
import os
from typing import Optional

from .controller import ModelServerController
from .enums import LogLevel, EnvVar
from .interfaces import IDownloadStrategy, ILogger, ISimulationService, ISpecService
from .services.download import HTTPDownloadStrategy, S3DownloadStrategy
from .services.image_processor import ImageProcessorFactory
from .services.logging import StructuredLogger
from .services.simulation import SimulationServiceFactory
from .services.spec_service import SpecServiceFactory


class ServerBootstrap:
    """Wires the server's services and controller from environment variables.

    Use ServerBootstrap.from_env() to construct a fully-initialized instance,
    then read the `controller` and `spec_service` properties.
    """

    def __init__(
        self,
        controller: ModelServerController,
        spec_service: ISpecService,
        logger: ILogger,
    ):
        self._controller = controller
        self._spec_service = spec_service
        self._logger = logger

    @property
    def controller(self) -> ModelServerController:
        return self._controller

    @property
    def spec_service(self) -> ISpecService:
        return self._spec_service

    @property
    def logger(self) -> ILogger:
        return self._logger

    @staticmethod
    def _env(name: str, default: str) -> str:
        """Read an env var, stripped; treat empty/whitespace-only as unset."""
        value = os.getenv(name)
        if value is None or not value.strip():
            return default
        return value.strip()

    @staticmethod
    def _build_download_strategy(
        url_template: str,
        logger: ILogger,
    ) -> IDownloadStrategy:
        """Pick S3 or HTTP download strategy based on the URL scheme."""
        if not url_template.startswith("s3://"):
            return HTTPDownloadStrategy(logger)

        access_key = os.getenv(EnvVar.SCW_ACCESS_KEY.value)
        secret_key = os.getenv(EnvVar.SCW_SECRET_KEY.value)
        if not access_key or not secret_key:
            raise EnvironmentError(
                f"{EnvVar.SCW_ACCESS_KEY.value} and {EnvVar.SCW_SECRET_KEY.value} "
                "must be set when an s3:// URL template is used"
            )
        return S3DownloadStrategy(
            logger=logger,
            access_key=access_key,
            secret_key=secret_key,
            region=os.getenv(EnvVar.SCW_REGION.value, "fr-par"),
            endpoint_url=os.getenv(EnvVar.SCW_ENDPOINT_URL.value, "https://s3.fr-par.scw.cloud"),
        )

    @classmethod
    def from_env(cls, checkpoints_dir: str = "./checkpoints") -> "ServerBootstrap":
        """Construct and initialize the server stack from environment variables.

        Args:
            checkpoints_dir: Local directory for model/spec lookup and on-demand
                download cache. Flask uses "./checkpoints"; Modal points this at
                the baked-in models directory.
        """
        logger = StructuredLogger("ModelServer", LogLevel.INFO)
        image_processor = ImageProcessorFactory.create_standard_processor(logger)

        # _env strips and treats empty/whitespace-only values as unset.
        model_bucket = cls._env(EnvVar.MODEL_BUCKET.value, "daylight-factor")
        model_url_template = cls._env(
            EnvVar.MODEL_URL_TEMPLATE.value,
            f"https://{model_bucket}.s3.fr-par.scw.cloud/models/{{name}}.onnx",
        )
        download_strategy = cls._build_download_strategy(model_url_template, logger)

        simulation_service: ISimulationService = SimulationServiceFactory.create(
            checkpoints_dir=checkpoints_dir,
            download_strategy=download_strategy,
            image_processor=image_processor,
            logger=logger,
            model_url_template=model_url_template,
        )

        # Derive default spec URL from MODEL_URL_TEMPLATE: replace filename with spec.json
        # e.g. s3://bucket/{name}/model.onnx -> s3://bucket/{name}/spec.json
        default_spec_url = model_url_template.rsplit("/", 1)[0] + "/spec.json"
        spec_url_template = cls._env(EnvVar.SPEC_URL_TEMPLATE.value, default_spec_url)
        spec_download_strategy = cls._build_download_strategy(spec_url_template, logger)

        spec_service: ISpecService = SpecServiceFactory.create(
            checkpoints_dir=checkpoints_dir,
            download_strategy=spec_download_strategy,
            logger=logger,
            spec_url_template=spec_url_template,
        )

        controller = ModelServerController(simulation_service=simulation_service, logger=logger)
        controller.initialize()

        return cls(controller=controller, spec_service=spec_service, logger=logger)
