"""Modal adapter — the Modal-native equivalent of main.py.

Serves the same HTTP contract as the Flask server, as a single ASGI app under
one host so clients only change the base URL:
  - POST /run    (multipart: file, model, optional cond_vec)
  - GET  /spec   (?model=...)
  - GET  /status
  - GET  /warm   (prewarm trigger; no inference)

Everything runs on one GPU container. The cheap metadata routes (/spec, /status)
share it; for the daylight-factor flow the extra GPU time is negligible and the
single host keeps the orchestrator a config-only change.
"""
from typing import Any, Dict, Optional

import modal
import requests
from botocore.exceptions import ClientError
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.server.bootstrap import ServerBootstrap
from src.server.cond_vec import CondVecParser
from src.server.enums import ContentType, HTTPStatus, SpecKey, ResponseKey, ResponseStatus

from . import config
from .guards import BodySizeLimitMiddleware, ModelAllowlist
from .image import image, runtime_secrets

app = modal.App(config.APP_NAME)


def _spec_not_found(error: Exception) -> bool:
    """True if a spec fetch error means 'no spec.json' (S3 or HTTP 404)."""
    if isinstance(error, ClientError):
        return error.response["Error"]["Code"] == "404"
    if isinstance(error, requests.exceptions.HTTPError):
        return error.response is not None and error.response.status_code == 404
    return False


_cls_kwargs = dict(
    image=image,
    gpu=config.GPU,
    secrets=runtime_secrets,
    scaledown_window=config.SCALEDOWN_WINDOW,
    min_containers=config.MIN_CONTAINERS,
    max_containers=config.MAX_CONTAINERS,
    enable_memory_snapshot=config.ENABLE_MEMORY_SNAPSHOT,
)
if config.ENABLE_GPU_SNAPSHOT:
    _cls_kwargs["experimental_options"] = {"enable_gpu_snapshot": True}


@app.cls(**_cls_kwargs)
class InferenceService:
    """GPU container serving inference plus the metadata routes."""

    @modal.enter(snap=True)
    def setup(self) -> None:
        # CPU-side wiring (imports, service wiring), captured in the snapshot.
        self._ctx = ServerBootstrap.from_env(checkpoints_dir=config.BAKED_CHECKPOINTS_DIR)
        # With GPU snapshots, create the CUDA session here too so it is captured.
        if config.ENABLE_GPU_SNAPSHOT:
            self._warm_gpu()

    @modal.enter()
    def warm_gpu_post_restore(self) -> None:
        # Without GPU snapshots, the CUDA session must be created after restore
        # (snapshots run without a GPU attached).
        if not config.ENABLE_GPU_SNAPSHOT:
            self._warm_gpu()

    def _warm_gpu(self) -> None:
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

    @modal.asgi_app(requires_proxy_auth=config.REQUIRES_PROXY_AUTH)
    def web(self) -> FastAPI:
        return build_api(self._ctx)


def build_api(
    ctx: Any,
    max_request_bytes: int = config.MAX_REQUEST_BYTES,
    allowed_models: Optional[tuple[str, ...]] = None,
) -> FastAPI:
    """Build the model server's FastAPI app from a runtime context.

    Extracted from the Modal ``web()`` method so the routes are unit-testable with a
    plain FastAPI TestClient (pass a stub ctx exposing ``.controller`` /
    ``.spec_service``) — no Modal runtime needed. The guard params are overridable
    so tests can exercise the size-limit / allowlist with small fixtures.
    """
    api = FastAPI(title="Upskiller Model Server")
    api.add_middleware(BodySizeLimitMiddleware, max_bytes=max_request_bytes)
    # `is None` (not truthiness) so an explicit empty allowlist () means "allow
    # none" rather than silently falling back to the configured default.
    resolved_models = allowed_models if allowed_models is not None else config.ALLOWED_MODELS
    model_allowlist = ModelAllowlist(resolved_models)

    @api.get("/status")
    def status() -> Dict[str, Any]:
        return ctx.controller.get_status()

    @api.get("/warm")
    def warm() -> Dict[str, Any]:
        # Prewarm trigger: reaching this route has already run @modal.enter (setup +
        # GPU/model preload), so a 200 means the container is warm. Does no inference.
        # The orchestrator pings this fire-and-forget at request entry so the GPU cold
        # start overlaps the CPU stages instead of being paid serially on /spec or /run.
        return {"warm": True}

    @api.post("/run")
    async def run(
        file: UploadFile = File(...),
        model: str = Form(...),
        cond_vec: Optional[str] = Form(None),
    ) -> Dict[str, Any]:
        if not ContentType.is_image(file.content_type or ""):
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST.value, detail="File must be an image")
        model_allowlist.validate(model)
        try:
            cv = CondVecParser.parse(cond_vec)
        except ValueError as e:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST.value, detail=str(e))
        image_bytes = await file.read()
        result = ctx.controller.handle_simulation_request(image_bytes, model, cv)
        if result.get(ResponseKey.STATUS.value) == ResponseStatus.ERROR.value:
            return JSONResponse(result, status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        return result

    @api.get("/spec")
    def spec(model: str) -> Dict[str, Any]:
        model_allowlist.validate(model)
        try:
            spec_data = ctx.spec_service.get_spec(model)
        except (ClientError, FileNotFoundError, requests.exceptions.HTTPError) as e:
            if _spec_not_found(e):
                raise HTTPException(status_code=404, detail=f"spec.json not found for model '{model}'")
            ctx.logger.error(f"Failed to retrieve spec for model '{model}': {e}")
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value, detail="Failed to retrieve spec")
        return {
            "encoding_scheme": spec_data.get(SpecKey.ARCHITECTURE.value, {}).get(SpecKey.ENCODING_VERSION.value),
            "encoder_model_type": spec_data.get(SpecKey.TRAINING.value, {}).get(SpecKey.TARGET.value),
        }

    return api
