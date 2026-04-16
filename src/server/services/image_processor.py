"""Image preprocessing for model inference — mirrors DaylightDataset.__getitem__"""
from enum import IntEnum
from typing import Callable, Dict, Tuple

import cv2
import numpy as np

from ..interfaces import IImageProcessor, ILogger


class ChannelLayout(IntEnum):
    """How OpenCV decoded the source image's channel dimension.

    The integer value matches ``shape[-1]`` for 3D arrays; ``GRAYSCALE``
    additionally covers true 2D (H, W) inputs.
    """
    GRAYSCALE = 1            # (H, W) or (H, W, 1)
    GRAYSCALE_ALPHA = 2      # (H, W, 2) — luminance + alpha (e.g. v5 encodings)
    BGR = 3                  # (H, W, 3)
    BGRA = 4                 # (H, W, 4)


class StandardImageProcessor(IImageProcessor):
    """
    Preprocesses an encoded input image for model inference.

    Pipeline:
      1. Decode bytes with cv2 (alpha channel preserved)
      2. Reorder channels to RGB(A) using a per-layout strategy:
           - 1 channel  → kept as grayscale
           - 2 channels → broadcast luminance over R/G/B, keep alpha → RGBA
           - 3 channels → BGR  → RGB
           - 4 channels → BGRA → RGBA
         Any other channel count raises ``ValueError``.
      3. Normalize to [0, 1] (divide by 255)
      4. Resize to 384×384 with bilinear interpolation
      5. HWC → CHW (or add a leading channel dim for grayscale)
      6. Add batch dimension → (1, C, H, W) float32
    """

    def __init__(self, logger: ILogger, target_size: Tuple[int, int] = (384, 384)):
        self._logger = logger
        self._target_size = target_size
        # Strategy map keyed by detected channel layout. Avoids if/elif chains
        # and makes adding new layouts a one-line change.
        self._channel_handlers: Dict[ChannelLayout, Callable[[np.ndarray], np.ndarray]] = {
            ChannelLayout.GRAYSCALE: self._handle_grayscale,
            ChannelLayout.GRAYSCALE_ALPHA: self._handle_grayscale_alpha,
            ChannelLayout.BGR: self._handle_bgr,
            ChannelLayout.BGRA: self._handle_bgra,
        }

    @staticmethod
    def _handle_grayscale(img: np.ndarray) -> np.ndarray:
        # Collapse any trailing singleton channel dim → (H, W); the channel
        # axis is re-added downstream in the HWC→CHW step.
        return img[:, :, 0] if img.ndim == 3 else img

    @staticmethod
    def _handle_grayscale_alpha(img: np.ndarray) -> np.ndarray:
        # (H, W, 2) → (H, W, 4): broadcast luminance over R, G, B; keep alpha.
        gray = img[:, :, 0:1]
        alpha = img[:, :, 1:2]
        return np.concatenate([gray, gray, gray, alpha], axis=-1).copy()

    @staticmethod
    def _handle_bgr(img: np.ndarray) -> np.ndarray:
        return img[:, :, ::-1].copy()                 # BGR → RGB

    @staticmethod
    def _handle_bgra(img: np.ndarray) -> np.ndarray:
        return img[:, :, [2, 1, 0, 3]].copy()         # BGRA → RGBA

    @staticmethod
    def _detect_layout(img_np: np.ndarray) -> ChannelLayout:
        if img_np.ndim == 2:
            return ChannelLayout.GRAYSCALE
        if img_np.ndim == 3:
            try:
                return ChannelLayout(img_np.shape[-1])
            except ValueError:
                pass
        raise ValueError(
            f"Unsupported image shape {img_np.shape}: expected 2D grayscale "
            f"or 3D with 1, 2, 3 or 4 channels."
        )

    def preprocess(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

        if img_np is None:
            raise ValueError("Failed to decode image")

        layout = self._detect_layout(img_np)
        img_np = self._channel_handlers[layout](img_np)

        img_np = img_np.astype(np.float32) / 255.0

        # Resize with bilinear interpolation (matches DaylightDataset)
        img_np = cv2.resize(img_np, self._target_size, interpolation=cv2.INTER_LINEAR)

        # HWC → CHW (or add leading channel dim for grayscale)
        if img_np.ndim == 2:
            img_np = img_np[np.newaxis, :, :]          # (1, H, W)
        else:
            img_np = np.transpose(img_np, (2, 0, 1))   # (C, H, W)

        # Add batch dimension → (1, C, H, W)
        img_np = np.expand_dims(img_np, axis=0)

        self._logger.debug(
            f"Preprocessed layout={layout.name}, shape={img_np.shape}, "
            f"range=[{img_np.min():.3f}, {img_np.max():.3f}]"
        )
        return img_np


class ImageProcessorFactory:
    @staticmethod
    def create_standard_processor(logger: ILogger, target_size: Tuple[int, int] = (384, 384)) -> IImageProcessor:
        return StandardImageProcessor(logger=logger, target_size=target_size)
