import numpy as np
from typing import Dict, Any
from ..interfaces import IPredictionService, IModelLoader, IImageProcessor, ILogger


class ModelPredictionService(IPredictionService):
    """Service for making model simulations (ONNX or TorchScript)"""

    def __init__(
        self,
        model_loader: IModelLoader,
        image_processor: IImageProcessor,
        logger: ILogger
    ):
        self._model_loader = model_loader
        self._image_processor = image_processor
        self._logger = logger
        self._model = None

    def _ensure_model_loaded(self) -> None:
        """Ensure model is loaded and ready"""
        if self._model is None:
            self._logger.info("Loading model for first simulation")
            self._model = self._model_loader.load()

    def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Make simulation on image bytes using the loaded model.

        Args:
            image_bytes: Raw image bytes from HTTP upload

        Returns:
            Dict containing:
                - simulation: 2D list of predicted values [H, W]
                - shape: List [height, width] of simulation
                - status: "success" or "error"
                - error: Error message (only if status is "error")
        """
        try:
            self._ensure_model_loaded()

            # Preprocess image (returns numpy array)
            image_np = self._image_processor.preprocess(image_bytes)

            # Log input statistics
            self._logger.info(f"Input tensor shape: {image_np.shape}, dtype: {image_np.dtype}")
            self._logger.info(f"Input tensor - min: {image_np.min():.6f}, max: {image_np.max():.6f}, mean: {image_np.mean():.6f}")

            # Make simulation
            self._logger.debug(f"Running model inference")
            output = self._model(image_np)

            # Process output: squeeze and scale by 255
            output_np = output.squeeze() * 255
            output_list = output_np.tolist()

            # Log output statistics
            self._logger.info(f"Output tensor shape: {output_np.shape}")
            self._logger.info(f"Output tensor (scaled) - min: {output_np.min():.6f}, max: {output_np.max():.6f}, mean: {output_np.mean():.6f}")

            return {
                "simulation": output_list,
                "shape": list(output_np.shape),
                "status": "success"
            }

        except Exception as e:
            self._logger.error(f"Prediction failed: {str(e)}")
            return {
                "simulation": None,
                "shape": None,
                "status": "error",
                "error": str(e)
            }


class PredictionServiceFactory:
    """Factory for creating simulation services"""

    @staticmethod
    def create_model_simulation_service(
        model_loader: IModelLoader,
        image_processor: IImageProcessor,
        logger: ILogger
    ) -> IPredictionService:
        """Create model-based simulation service"""
        return ModelPredictionService(
            model_loader=model_loader,
            image_processor=image_processor,
            logger=logger
        )