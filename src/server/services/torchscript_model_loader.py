"""TorchScript and torch.export Model Loader for inference"""
from typing import Optional, Union
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod

import torch
import numpy as np

from ..interfaces import IModelLoader, IDownloadStrategy, ILogger
from ..enums import ModelStatus


class ModelFormat(Enum):
    """Supported model formats"""
    TORCHSCRIPT = "torchscript"
    TORCH_EXPORT = "torch_export"
    AUTO = "auto"


class TorchInferenceWrapper(ABC):
    """Base wrapper for PyTorch model inference"""

    @abstractmethod
    def __call__(self, input_tensor: np.ndarray) -> np.ndarray:
        """Run inference on input tensor"""
        pass

    def eval(self):
        """Set model to evaluation mode"""
        pass

    def to(self, device: str):
        """Move model to device"""
        return self


class TorchScriptInferenceWrapper(TorchInferenceWrapper):
    """Wrapper for TorchScript model inference"""

    def __init__(self, model: torch.jit.ScriptModule, device: str = "cpu"):
        self._model = model
        self._device = device
        self._model.to(device)
        self._model.eval()

    def __call__(self, input_tensor: np.ndarray) -> np.ndarray:
        """Run inference on numpy input tensor"""
        # Convert numpy to torch tensor
        torch_input = torch.from_numpy(input_tensor).to(self._device)

        # Run inference
        with torch.no_grad():
            output = self._model(torch_input)

        # Convert back to numpy
        return output.cpu().numpy()

    def to(self, device: str):
        """Move model to device"""
        self._device = device
        self._model.to(device)
        return self


class TorchExportInferenceWrapper(TorchInferenceWrapper):
    """Wrapper for torch.export model inference"""

    def __init__(self, exported_program, device: str = "cpu"):
        self._exported_program = exported_program
        self._device = device
        # torch.export models are already optimized, just need device handling

    def __call__(self, input_tensor: np.ndarray) -> np.ndarray:
        """Run inference on numpy input tensor"""
        # Convert numpy to torch tensor
        torch_input = torch.from_numpy(input_tensor).to(self._device)

        # Run inference using exported program
        with torch.no_grad():
            output = self._exported_program.module()(torch_input)

        # Convert back to numpy
        return output.cpu().numpy()

    def to(self, device: str):
        """Move model to device (limited support for torch.export)"""
        self._device = device
        # Note: torch.export models may have limited device transfer support
        return self


class FormatDetector:
    """Detects model format from file extension or content"""

    @staticmethod
    def detect_from_path(model_path: str) -> ModelFormat:
        """Detect format from file extension"""
        ext = Path(model_path).suffix.lower()

        format_map = {
            '.pt': ModelFormat.TORCHSCRIPT,
            '.pth': ModelFormat.TORCHSCRIPT,
            '.pt2': ModelFormat.TORCH_EXPORT,
        }

        return format_map.get(ext, ModelFormat.TORCHSCRIPT)


class ModelLoaderStrategy(ABC):
    """Base class for model loading strategies"""

    @abstractmethod
    def load_model(self, model_path: str, device: str) -> TorchInferenceWrapper:
        """Load model and return inference wrapper"""
        pass


class TorchScriptLoaderStrategy(ModelLoaderStrategy):
    """Strategy for loading TorchScript models"""

    def __init__(self, logger: ILogger):
        self._logger = logger

    def load_model(self, model_path: str, device: str) -> TorchScriptInferenceWrapper:
        """Load TorchScript model"""
        self._logger.info(f"Loading TorchScript model from: {model_path}")

        try:
            model = torch.jit.load(model_path, map_location=device)
            model.eval()

            self._logger.info(f"TorchScript model loaded successfully on device: {device}")
            return TorchScriptInferenceWrapper(model, device)

        except Exception as e:
            self._logger.error(f"Failed to load TorchScript model: {str(e)}")
            raise


class TorchExportLoaderStrategy(ModelLoaderStrategy):
    """Strategy for loading torch.export models"""

    def __init__(self, logger: ILogger):
        self._logger = logger

    def load_model(self, model_path: str, device: str) -> TorchExportInferenceWrapper:
        """Load torch.export model"""
        self._logger.info(f"Loading torch.export model from: {model_path}")

        try:
            # torch.export models are loaded on CPU by default
            # Device transfer has limited support in torch.export
            self._logger.warning(f"torch.export models currently run on CPU only (requested: {device})")
            exported_program = torch.export.load(model_path)

            self._logger.info(f"torch.export model loaded successfully on CPU")
            return TorchExportInferenceWrapper(exported_program, "cpu")

        except Exception as e:
            self._logger.error(f"Failed to load torch.export model: {str(e)}")
            raise


class TorchScriptModelLoader(IModelLoader):
    """Model loader for TorchScript and torch.export format models"""

    def __init__(
        self,
        model_url: str,
        local_path: str,
        download_strategy: IDownloadStrategy,
        logger: ILogger,
        device: Optional[str] = None,
        model_format: ModelFormat = ModelFormat.AUTO
    ):
        self._model_url = model_url
        self._local_path = local_path
        self._download_strategy = download_strategy
        self._logger = logger
        self._device = device or self._detect_device()
        self._model_format = model_format
        self._model: Optional[TorchInferenceWrapper] = None
        self._status = ModelStatus.LOADING
        self._loader_strategy: Optional[ModelLoaderStrategy] = None

    @staticmethod
    def _detect_device() -> str:
        """Detect best available device"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    def _get_loader_strategy(self, model_path: str) -> ModelLoaderStrategy:
        """Get appropriate loader strategy based on format"""
        # Auto-detect format if needed
        if self._model_format == ModelFormat.AUTO:
            detected_format = FormatDetector.detect_from_path(model_path)
            self._logger.info(f"Auto-detected model format: {detected_format.value}")
        else:
            detected_format = self._model_format

        # Create strategy
        strategy_map = {
            ModelFormat.TORCHSCRIPT: TorchScriptLoaderStrategy(self._logger),
            ModelFormat.TORCH_EXPORT: TorchExportLoaderStrategy(self._logger),
        }

        return strategy_map[detected_format]

    @property
    def status(self) -> ModelStatus:
        return self._status

    def load(self) -> TorchInferenceWrapper:
        """Load model using appropriate strategy"""
        try:
            self._status = ModelStatus.LOADING
            self._logger.info("Starting PyTorch model loading process")
            self._logger.info(f"Target device: {self._device}")

            # Download model if URL provided
            if self._model_url:
                model_path = self._download_strategy.download(
                    self._model_url,
                    self._local_path
                )
            else:
                model_path = self._local_path

            # Get loader strategy and load model
            self._loader_strategy = self._get_loader_strategy(model_path)
            self._model = self._loader_strategy.load_model(model_path, self._device)

            self._status = ModelStatus.READY
            self._logger.info("Model loaded and ready for inference")

            return self._model

        except Exception as e:
            self._status = ModelStatus.ERROR
            self._logger.error(f"Model loading failed: {str(e)}")
            raise

    def get_model(self) -> TorchInferenceWrapper:
        """Get the loaded model"""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        return self._model
