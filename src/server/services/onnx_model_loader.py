"""ONNX Model Loader for inference without exposing model architecture"""
import numpy as np
import onnxruntime as ort
from typing import Optional
from ..interfaces import IModelLoader, IDownloadStrategy, ILogger
from ..enums import ModelStatus


class ONNXInferenceWrapper:
    """Wrapper for ONNX Runtime inference session"""

    def __init__(self, session: ort.InferenceSession):
        self._session = session
        self._input_name = session.get_inputs()[0].name
        self._output_name = session.get_outputs()[0].name

    def __call__(self, input_tensor: np.ndarray) -> np.ndarray:
        """Run inference on input tensor"""
        # Run inference with preprocessed image
        onnx_input = {self._input_name: input_tensor}
        onnx_output = self._session.run(None, onnx_input)
        return onnx_output[0]

    def eval(self):
        """Compatibility method - ONNX models are always in eval mode"""
        pass

    def to(self, device: str):
        """Compatibility method - device is set during session creation"""
        return self


class ONNXModelLoader(IModelLoader):
    """Model loader for ONNX format models"""

    def __init__(
        self,
        model_url: str,
        local_path: str,
        download_strategy: IDownloadStrategy,
        logger: ILogger,
        providers: Optional[list] = None
    ):
        self._model_url = model_url
        self._local_path = local_path
        self._download_strategy = download_strategy
        self._logger = logger
        self._providers = providers or self._get_default_providers()
        self._model: Optional[ONNXInferenceWrapper] = None
        self._status = ModelStatus.LOADING

    @staticmethod
    def _get_default_providers() -> list:
        """Get available execution providers in order of preference"""
        available_providers = ort.get_available_providers()
        preferred_order = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        return [p for p in preferred_order if p in available_providers]

    @property
    def status(self) -> ModelStatus:
        return self._status

    def load(self) -> ONNXInferenceWrapper:
        """Load ONNX model"""
        try:
            self._status = ModelStatus.LOADING
            self._logger.info("Starting ONNX model loading process")

            # Download model if URL provided
            if self._model_url:
                model_path = self._download_strategy.download(
                    self._model_url,
                    self._local_path
                )
            else:
                model_path = self._local_path

            # Create ONNX Runtime session
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            session = ort.InferenceSession(
                model_path,
                sess_options=session_options,
                providers=self._providers
            )

            self._model = ONNXInferenceWrapper(session)
            self._status = ModelStatus.READY

            provider_info = session.get_providers()[0]
            self._logger.info(f"ONNX model loaded successfully with provider: {provider_info}")

            return self._model

        except Exception as e:
            self._status = ModelStatus.ERROR
            self._logger.error(f"ONNX model loading failed: {str(e)}")
            raise

    def get_model(self) -> ONNXInferenceWrapper:
        """Get the loaded ONNX model"""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        return self._model
