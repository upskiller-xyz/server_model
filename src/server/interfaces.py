from abc import ABC, abstractmethod
from typing import Any, Dict, List
import torch
import numpy as np
from PIL import Image


class IModelLoader(ABC):
    """Interface for model loading strategies"""

    @abstractmethod
    def load(self) -> torch.nn.Module:
        """Load and return the model"""
        pass


class IImageProcessor(ABC):
    """Interface for image processing strategies"""

    @abstractmethod
    def preprocess(self, image_bytes: bytes) -> torch.Tensor:
        """Preprocess image bytes into tensor"""
        pass


class IDownloadStrategy(ABC):
    """Interface for download strategies"""

    @abstractmethod
    def download(self, url: str, local_path: str) -> str:
        """Download file from URL to local path"""
        pass


class ILogger(ABC):
    """Interface for logging strategies"""

    @abstractmethod
    def debug(self, message: str) -> None:
        pass

    @abstractmethod
    def info(self, message: str) -> None:
        pass

    @abstractmethod
    def warning(self, message: str) -> None:
        pass

    @abstractmethod
    def error(self, message: str) -> None:
        pass


class IPredictionService(ABC):
    """Interface for simulation services"""

    @abstractmethod
    def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        """Make simulation on image and return result"""
        pass


class IServerController(ABC):
    """Interface for server controllers"""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the server"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get server status"""
        pass