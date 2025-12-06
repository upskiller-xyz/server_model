"""Model loader factory - supports ONNX, TorchScript, and torch.export"""
from typing import Dict, Callable
from ..interfaces import IModelLoader
from .onnx_model_loader import ONNXModelLoader
from .torchscript_model_loader import TorchScriptModelLoader


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

    @classmethod
    def get_available_loaders(cls) -> list[str]:
        """Get list of available loader types"""
        return list(cls._loaders.keys())


# Register all loaders
ModelLoaderFactory.register_loader("onnx", ONNXModelLoader)
ModelLoaderFactory.register_loader("torchscript", TorchScriptModelLoader)
ModelLoaderFactory.register_loader("torch_export", TorchScriptModelLoader)
ModelLoaderFactory.register_loader("pytorch", TorchScriptModelLoader)  # Alias
