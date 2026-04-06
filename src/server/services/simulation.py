import re
import threading
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import Dict, Any, Optional
from ..interfaces import ISimulationService, IDownloadStrategy, IImageProcessor, ILogger
from .onnx_model_loader import ONNXInferenceWrapper


_MODEL_URL_TEMPLATE = "https://daylight-factor.s3.fr-par.scw.cloud/models/{name}.onnx"
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ModelSimulationService(ISimulationService):
    """
    Simulation service that supports multiple models.

    Model resolution per request:
      1. Client passes model name (e.g. "df_default_2.0.1") in the request.
      2. Server looks for ./checkpoints/<name>.onnx locally.
      3. If not found, downloads from the model registry URL.
      4. Loaded sessions are cached in memory by model name.
      5. Whether cond_vec is used is determined by the model itself (has_cond_vec).
    """

    def __init__(
        self,
        checkpoints_dir: str,
        download_strategy: IDownloadStrategy,
        image_processor: IImageProcessor,
        logger: ILogger,
    ):
        self._checkpoints_dir = Path(checkpoints_dir)
        self._download_strategy = download_strategy
        self._image_processor = image_processor
        self._logger = logger
        self._cache: Dict[str, ONNXInferenceWrapper] = {}
        self._lock = threading.Lock()

    def _validate_model_name(self, model_name: str) -> None:
        if not _MODEL_NAME_RE.match(model_name):
            raise ValueError(f"Invalid model name: '{model_name}'")
        resolved = (self._checkpoints_dir / f"{model_name}.onnx").resolve()
        if not resolved.is_relative_to(self._checkpoints_dir.resolve()):
            raise ValueError(f"Model path escapes checkpoints directory: '{model_name}'")

    def _load_model(self, model_name: str) -> ONNXInferenceWrapper:
        """Load ONNX model by name, downloading if necessary."""
        self._validate_model_name(model_name)
        local_path = self._checkpoints_dir / f"{model_name}.onnx"

        if not local_path.exists():
            url = _MODEL_URL_TEMPLATE.format(name=model_name)
            self._logger.info(f"Downloading model '{model_name}' from {url}")
            self._download_strategy.download(url, str(local_path))

        providers = [p for p in ['CUDAExecutionProvider', 'CPUExecutionProvider']
                     if p in ort.get_available_providers()]
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session = ort.InferenceSession(str(local_path), sess_options=session_options, providers=providers)

        wrapper = ONNXInferenceWrapper(session)
        self._logger.info(f"Model '{model_name}' loaded (provider: {session.get_providers()[0]}, has_cond_vec: {wrapper.has_cond_vec})")
        return wrapper

    def _get_model(self, model_name: str) -> ONNXInferenceWrapper:
        if model_name not in self._cache:
            with self._lock:
                if model_name not in self._cache:  # double-checked locking
                    self._cache[model_name] = self._load_model(model_name)
        return self._cache[model_name]

    def simulate(
        self,
        image_bytes: bytes,
        model_name: str,
        cond_vec: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        try:
            model = self._get_model(model_name)

            image_np = self._image_processor.preprocess(image_bytes)  # (1, C, H, W) in [0, 1]

            # Pass cond_vec only if the model expects it
            cv = cond_vec if model.has_cond_vec else None
            if model.has_cond_vec and cond_vec is None:
                self._logger.warning(f"Model '{model_name}' expects cond_vec but none was provided")

            output = model(image_np, cv)          # (1, 1, H, W)
            output_np = output.squeeze() * 255    # (H, W) in [0, 255]

            self._logger.info(f"Output shape: {output_np.shape}, range: [{output_np.min():.3f}, {output_np.max():.3f}]")

            return {
                "simulation": output_np.tolist(),
                "shape": list(output_np.shape),
                "status": "success",
            }

        except Exception as e:
            self._logger.error(f"Simulation failed: {e}")
            return {"simulation": None, "shape": None, "status": "error", "error": str(e)}


class SimulationServiceFactory:
    @staticmethod
    def create(
        checkpoints_dir: str,
        download_strategy: IDownloadStrategy,
        image_processor: IImageProcessor,
        logger: ILogger,
    ) -> ISimulationService:
        return ModelSimulationService(
            checkpoints_dir=checkpoints_dir,
            download_strategy=download_strategy,
            image_processor=image_processor,
            logger=logger,
        )
