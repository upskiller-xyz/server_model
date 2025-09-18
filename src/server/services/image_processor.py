import torch
import torchvision.transforms as transforms
from PIL import Image
import io
from typing import Tuple
from ..interfaces import IImageProcessor, ILogger


class StandardImageProcessor(IImageProcessor):
    """Standard image preprocessing for computer vision models"""

    def __init__(
        self,
        logger: ILogger,
        target_size: Tuple[int, int] = (384, 384),
        normalize_mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
        normalize_std: Tuple[float, float, float] = (0.229, 0.224, 0.225)
    ):
        self._logger = logger
        self._target_size = target_size
        self._normalize_mean = normalize_mean
        self._normalize_std = normalize_std
        self._transform = self._create_transform()

    def _create_transform(self) -> transforms.Compose:
        """Create the image transformation pipeline"""
        return transforms.Compose([
            transforms.Resize(self._target_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=self._normalize_mean,
                std=self._normalize_std
            )
        ])

    def preprocess(self, image_bytes: bytes) -> torch.Tensor:
        """Preprocess image bytes into tensor"""
        try:
            self._logger.debug("Starting image preprocessing")

            # Load image from bytes
            image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                self._logger.debug(f"Converting image from {image.mode} to RGB")
                image = image.convert('RGB')

            # Apply transformations
            image_tensor = self._transform(image)

            # Add batch dimension
            image_tensor = image_tensor.unsqueeze(0)

            self._logger.debug(f"Image preprocessed to shape: {image_tensor.shape}")
            return image_tensor

        except Exception as e:
            self._logger.error(f"Image preprocessing failed: {str(e)}")
            raise


class ImageProcessorFactory:
    """Factory for creating image processors"""

    @staticmethod
    def create_standard_processor(logger: ILogger) -> IImageProcessor:
        """Create standard image processor"""
        return StandardImageProcessor(logger)

    @staticmethod
    def create_custom_processor(
        logger: ILogger,
        target_size: Tuple[int, int],
        normalize_mean: Tuple[float, float, float],
        normalize_std: Tuple[float, float, float]
    ) -> IImageProcessor:
        """Create custom image processor"""
        return StandardImageProcessor(
            logger=logger,
            target_size=target_size,
            normalize_mean=normalize_mean,
            normalize_std=normalize_std
        )