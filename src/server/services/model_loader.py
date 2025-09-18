import torch
from typing import Dict, Callable
from ..interfaces import IModelLoader, IDownloadStrategy, ILogger
from ..enums import ModelStatus
from ...model.glp_based_model import GlpModel



class GlpModelLoader(IModelLoader):
    """Model loader specifically for GLP-based models"""

    def __init__(
        self,
        checkpoint_url: str,
        local_path: str,
        download_strategy: IDownloadStrategy,
        logger: ILogger,
        batch_size: int = 1,
        decoders_channels_in: list = None,
        decoders_channels_out: int = 64
    ):
        self._checkpoint_url = checkpoint_url
        self._local_path = local_path
        self._download_strategy = download_strategy
        self._logger = logger
        self._batch_size = batch_size
        self._decoders_channels_in = decoders_channels_in
        self._decoders_channels_out = decoders_channels_out
        self._model: torch.nn.Module = None
        self._status = ModelStatus.LOADING

    @property
    def status(self) -> ModelStatus:
        return self._status

    def load(self) -> torch.nn.Module:
        """Load GLP model from checkpoint"""
        try:
            self._status = ModelStatus.LOADING
            self._logger.info("Starting GLP model loading process")

            # Download checkpoint if URL provided
            if self._checkpoint_url:
                checkpoint_path = self._download_strategy.download(
                    self._checkpoint_url,
                    self._local_path
                )
            else:
                checkpoint_path = self._local_path

            # Load model from checkpoint
            self._model = GlpModel.load_from_checkpoint(
                checkpoint_path,
                batch_size=self._batch_size
            )

            # Setup for inference
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model.to(device)
            self._model.eval()

            self._status = ModelStatus.READY
            self._logger.info(f"GLP model loaded successfully on device: {device}")

            return self._model

        except Exception as e:
            self._status = ModelStatus.ERROR
            self._logger.error(f"GLP model loading failed: {str(e)}")
            raise

    def get_model(self) -> torch.nn.Module:
        """Get the loaded GLP model"""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        return self._model


class ModelLoaderFactory:
    """Factory for creating model loaders"""

    _loaders: Dict[str, Callable[..., IModelLoader]] = {}

    @classmethod
    def register_loader(cls, loader_type: str, loader_class: Callable[..., IModelLoader]) -> None:
        """Register a model loader type"""
        cls._loaders[loader_type] = loader_class

    @classmethod
    def create_loader(cls, loader_type: str, **kwargs) -> IModelLoader:
        """Create a model loader of specified type"""
        if loader_type not in cls._loaders:
            raise ValueError(f"Unknown loader type: {loader_type}")

        return cls._loaders[loader_type](**kwargs)


# Register default loaders
ModelLoaderFactory.register_loader("glp", GlpModelLoader)