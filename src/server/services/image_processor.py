"""Image preprocessing for model inference — mirrors DaylightDataset.__getitem__"""
import numpy as np
import cv2
from typing import Tuple
from ..interfaces import IImageProcessor, ILogger


class StandardImageProcessor(IImageProcessor):
    """
    Preprocesses an encoded input image to match DaylightDataset.__getitem__:
      1. Decode bytes with cv2 (preserve all channels including alpha)
      2. BGR→RGB for 3-channel images, BGRA→RGBA for 4-channel images
      3. Normalize to [0, 1]  (divide by 255)
      4. Resize to 384×384 with bilinear interpolation
      5. HWC → CHW
      6. Add batch dimension → (1, C, H, W) float32

    Note: 4-channel images (HSVA) must NOT have the alpha channel dropped.
    The alpha channel encodes the obstruction bar — it is a model input, not
    image transparency. Models trained with encoding v2 expect 4 channels.
    """

    def __init__(self, logger: ILogger, target_size: Tuple[int, int] = (384, 384)):
        self._logger = logger
        self._target_size = target_size

    def preprocess(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

        if img_np is None:
            raise ValueError("Failed to decode image")

        # BGR → RGB (cv2 loads colour images as BGR)
        # BGRA → RGBA for 4-channel images (alpha = obstruction bar, must be preserved)
        if img_np.ndim == 3 and img_np.shape[-1] == 3:
            img_np = img_np[:, :, ::-1].copy()
        elif img_np.ndim == 3 and img_np.shape[-1] == 4:
            img_np = img_np[:, :, [2, 1, 0, 3]].copy()  # BGRA → RGBA

        img_np = img_np.astype(np.float32)

        # Normalize to [0, 1]
        img_np = img_np / 255.0

        # Resize with bilinear interpolation (matches DaylightDataset)
        img_np = cv2.resize(img_np, self._target_size, interpolation=cv2.INTER_LINEAR)

        # HWC → CHW
        if img_np.ndim == 2:
            img_np = img_np[np.newaxis, :, :]          # (1, H, W)
        else:
            img_np = np.transpose(img_np, (2, 0, 1))   # (C, H, W)

        # Add batch dimension → (1, C, H, W)
        img_np = np.expand_dims(img_np, axis=0)

        self._logger.debug(f"Preprocessed shape: {img_np.shape}, range: [{img_np.min():.3f}, {img_np.max():.3f}]")
        return img_np


class ImageProcessorFactory:
    @staticmethod
    def create_standard_processor(logger: ILogger, target_size: Tuple[int, int] = (384, 384)) -> IImageProcessor:
        return StandardImageProcessor(logger=logger, target_size=target_size)
