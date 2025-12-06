"""Image preprocessing for ONNX and TorchScript models"""
import numpy as np
import cv2
from typing import Tuple
from ..interfaces import IImageProcessor, ILogger


class StandardImageProcessor(IImageProcessor):
    """
    Standard image preprocessing pipeline for model inference.

    Pipeline:
    1. Load image from bytes using cv2
    2. Take only first 3 channels (RGB) if image has alpha
    3. Reverse BGR to RGB
    4. Normalize to [-1, 1] range: (pixel / 127.5) - 1
    5. Resize to target size using NEAREST interpolation
    6. Convert HWC to CHW format
    7. Add batch dimension [1, C, H, W]
    """

    def __init__(
        self,
        logger: ILogger,
        target_size: Tuple[int, int] = (384, 384)
    ):
        self._logger = logger
        self._target_size = target_size

    def preprocess(self, image_bytes: bytes) -> np.ndarray:
        """
        Preprocess image bytes into numpy array for model inference.

        Args:
            image_bytes: Raw image bytes from file upload

        Returns:
            np.ndarray: Preprocessed image tensor with shape [1, 3, H, W]
                       and values in range [-1, 1]
        """
        try:
            self._logger.debug("Starting image preprocessing")

            # Step 1: Load image using cv2 (same as BytesImageLoader)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img_np = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

            if img_np is None:
                raise ValueError("Failed to decode image")

            self._logger.debug(f"After cv2.imdecode - shape: {img_np.shape}, dtype: {img_np.dtype}")

            # Step 2: Take only first 3 channels (RGB), drop alpha if present
            if img_np.ndim == 3 and img_np.shape[-1] > 3:
                img_np = img_np[:, :, :3]
                self._logger.debug(f"After removing alpha channel - shape: {img_np.shape}")

            # Step 3: Reverse BGR to RGB (cv2 loads as BGR)
            if img_np.ndim == 3 and img_np.shape[-1] == 3:
                img_np = img_np[:, :, ::-1].copy()
                self._logger.debug("Reversed BGR to RGB")

            # Convert to float32 for normalization
            img_np = img_np.astype(np.float32)

            # Step 4: Normalize to [-1, 1] range
            img_np = (img_np / 127.5) - 1.0
            self._logger.info(f"After normalization - min: {img_np.min():.6f}, max: {img_np.max():.6f}, mean: {img_np.mean():.6f}")

            # Step 5: Resize to target size
            img_np = cv2.resize(img_np, self._target_size, interpolation=cv2.INTER_NEAREST)
            self._logger.debug(f"After resize - shape: {img_np.shape}")

            # Step 6: Convert from HWC to CHW format
            img_np = np.transpose(img_np, (2, 0, 1))

            # Step 7: Add batch dimension [1, C, H, W]
            img_np = np.expand_dims(img_np, axis=0)

            self._logger.info(f"Final preprocessed shape: {img_np.shape}, dtype: {img_np.dtype}")
            self._logger.info(f"Final range - min: {img_np.min():.6f}, max: {img_np.max():.6f}")

            return img_np

        except Exception as e:
            self._logger.error(f"Image preprocessing failed: {str(e)}")
            raise


class ImageProcessorFactory:
    """Factory for creating image processors"""

    @staticmethod
    def create_standard_processor(logger: ILogger, target_size: Tuple[int, int] = (384, 384)) -> IImageProcessor:
        """
        Create standard image processor with default settings.

        Args:
            logger: Logger instance for debugging
            target_size: Target size for resizing (default: 384x384)

        Returns:
            IImageProcessor: Configured image processor
        """
        return StandardImageProcessor(logger=logger, target_size=target_size)

    @staticmethod
    def create_custom_processor(
        logger: ILogger,
        target_size: Tuple[int, int]
    ) -> IImageProcessor:
        """
        Create custom image processor with specified settings.

        Args:
            logger: Logger instance for debugging
            target_size: Target size for resizing

        Returns:
            IImageProcessor: Configured image processor
        """
        return StandardImageProcessor(
            logger=logger,
            target_size=target_size
        )
