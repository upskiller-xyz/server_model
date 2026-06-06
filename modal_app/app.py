"""Modal adapter — the Modal-native equivalent of main.py.

Exposes the same HTTP contract as the Flask server so clients only change the
base URL:
  - POST /run   (multipart: file, model, optional cond_vec)  -> GPU container
  - GET  /spec  (?model=...)                                 -> CPU container
  - GET  /status                                             -> CPU container

GPU inference and the cheap metadata endpoints run on separate containers so a
health check or spec lookup never spins up an L4.
"""
from typing import Any, Dict, Optional

import modal
from botocore.exceptions import ClientError
from fastapi import Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.server.bootstrap import ServerBootstrap
from src.server.cond_vec import CondVecParser
from src.server.enums import ContentType, HTTPStatus, SpecKey

from . import config
from .image import image, scaleway_secret

app = modal.App(config.APP_NAME)


@app.cls(
    image=image,
    gpu=config.GPU,
    secrets=[scaleway_secret],
    scaledown_window=config.SCALEDOWN_WINDOW,
    min_containers=config.MIN_CONTAINERS,
)
class InferenceService:
    """GPU container running ONNX daylight-factor inference."""

    @modal.enter()
    def load(self) -> None:
        self._ctx = ServerBootstrap.from_env(checkpoints_dir=config.BAKED_CHECKPOINTS_DIR)
        self._verify_gpu()
        for name in config.BAKED_MODELS:
            self._ctx.controller.preload_model(name)
            self._ctx.logger.info(f"Preloaded baked model '{name}'")

    def _verify_gpu(self) -> None:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        self._ctx.logger.info(f"ONNX providers available: {providers}")
        if "CUDAExecutionProvider" not in providers:
            self._ctx.logger.warning("CUDAExecutionProvider unavailable — inference will run on CPU")

    @modal.fastapi_endpoint(method="POST", requires_proxy_auth=config.REQUIRES_PROXY_AUTH)
    async def run(
        self,
        file: UploadFile,
        model: str = Form(...),
        cond_vec: Optional[str] = Form(None),
    ) -> Dict[str, Any]:
        if not ContentType.is_image(file.content_type or ""):
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST.value, detail="File must be an image")

        try:
            cv = CondVecParser.parse(cond_vec)
        except ValueError as e:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST.value, detail=str(e))
        image_bytes = await file.read()
        result = self._ctx.controller.handle_simulation_request(image_bytes, model, cv)

        if result.get("status") == "error":
            return JSONResponse(result, status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        return result


@app.cls(
    image=image,
    secrets=[scaleway_secret],
    scaledown_window=config.SCALEDOWN_WINDOW,
)
class MetadataService:
    """CPU container for status and spec lookups (no GPU needed)."""

    @modal.enter()
    def load(self) -> None:
        self._ctx = ServerBootstrap.from_env(checkpoints_dir=config.BAKED_CHECKPOINTS_DIR)

    @modal.fastapi_endpoint(method="GET", requires_proxy_auth=config.REQUIRES_PROXY_AUTH)
    def status(self) -> Dict[str, Any]:
        return self._ctx.controller.get_status()

    @modal.fastapi_endpoint(method="GET", requires_proxy_auth=config.REQUIRES_PROXY_AUTH)
    def spec(self, model: str) -> Dict[str, Any]:
        try:
            spec = self._ctx.spec_service.get_spec(model)
        except (ClientError, FileNotFoundError) as e:
            if isinstance(e, ClientError) and e.response["Error"]["Code"] == "404":
                raise HTTPException(status_code=404, detail=f"spec.json not found for model '{model}'")
            self._ctx.logger.error(f"Failed to retrieve spec for model '{model}': {e}")
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value, detail="Failed to retrieve spec")
        return {
            "encoding_scheme": spec.get(SpecKey.ARCHITECTURE.value, {}).get(SpecKey.ENCODING_VERSION.value),
            "encoder_model_type": spec.get(SpecKey.TRAINING.value, {}).get(SpecKey.TARGET.value),
        }
