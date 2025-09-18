import torch
import numpy as np
from typing import Dict, Any
from ..interfaces import IPredictionService, IModelLoader, IImageProcessor, ILogger
from ..enums import ModelStatus


class ModelPredictionService(IPredictionService):
    """Service for making model predictions"""

    def __init__(
        self,
        model_loader: IModelLoader,
        image_processor: IImageProcessor,
        logger: ILogger
    ):
        self._model_loader = model_loader
        self._image_processor = image_processor
        self._logger = logger
        self._model: torch.nn.Module = None
        self._device: torch.device = None

    def _ensure_model_loaded(self) -> None:
        """Ensure model is loaded and ready"""
        if self._model is None:
            self._logger.info("Loading model for first prediction")
            self._model = self._model_loader.load()
            self._device = next(self._model.parameters()).device

    def predict(self, image_bytes: bytes) -> Dict[str, Any]:
        """Make prediction on image bytes"""
        try:
            self._ensure_model_loaded()

            # Preprocess image
            image_tensor = self._image_processor.preprocess(image_bytes)
            image_tensor = image_tensor.to(self._device)

            # Make prediction
            self._logger.debug("Running model inference")
            with torch.no_grad():
                output = self._model(image_tensor)

            # Process output
            output_np = output.cpu().numpy().squeeze()
            output_list = output_np.tolist()

            self._logger.debug(f"Prediction completed, output shape: {output_np.shape}")

            return {
                "prediction": output_list,
                "shape": list(output_np.shape),
                "status": "success"
            }

        except Exception as e:
            self._logger.error(f"Prediction failed: {str(e)}")
            return {
                "prediction": None,
                "shape": None,
                "status": "error",
                "error": str(e)
            }


class PredictionServiceFactory:
    """Factory for creating prediction services"""

    @staticmethod
    def create_model_prediction_service(
        model_loader: IModelLoader,
        image_processor: IImageProcessor,
        logger: ILogger
    ) -> IPredictionService:
        """Create model-based prediction service"""
        return ModelPredictionService(
            model_loader=model_loader,
            image_processor=image_processor,
            logger=logger
        )