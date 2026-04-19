from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import numpy as np


class IImageProcessor(ABC):
    @abstractmethod
    def preprocess(self, image_bytes: bytes) -> np.ndarray: ...


class IDownloadStrategy(ABC):
    @abstractmethod
    def download(self, url: str, local_path: str) -> str: ...


class ILogger(ABC):
    @abstractmethod
    def debug(self, message: str) -> None: ...

    @abstractmethod
    def info(self, message: str) -> None: ...

    @abstractmethod
    def warning(self, message: str) -> None: ...

    @abstractmethod
    def error(self, message: str) -> None: ...


class ISimulationService(ABC):
    @abstractmethod
    def simulate(
        self,
        image_bytes: bytes,
        model_name: str,
        cond_vec: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]: ...


class IModelLoader(ABC):
    @abstractmethod
    def load(self) -> Any: ...

    @abstractmethod
    def get_model(self) -> Any: ...


class ISpecService(ABC):
    @abstractmethod
    def get_spec(self, model_name: str) -> Dict[str, Any]: ...


class IServerController(ABC):
    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def get_status(self) -> Dict[str, Any]: ...
