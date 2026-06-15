"""Configuration constants for the Modal deployment.

Centralizes every tunable value (GPU type, baked models, scaling, auth, URLs)
so the app/image modules contain no magic strings.
"""
from typing import Optional

# Modal app name (shown in the dashboard and in deployed endpoint URLs).
APP_NAME = "upskiller-model"

# GPU class for the inference container.
GPU = "L4"

# Seconds a warm container is kept alive after its last request (cold-start vs cost).
# 60s: scale to zero quickly to minimise idle cost; trades more frequent cold starts
# (mitigated by the /warm prewarm path) for a shorter idle tail.
SCALEDOWN_WINDOW = 60

# Containers kept permanently warm. 0 = scale to zero (cheapest, cold starts).
MIN_CONTAINERS = 0

# Memory snapshots: snapshot the container after init and restore it on cold
# start instead of re-initializing — cuts cold-start latency with no idle cost.
ENABLE_MEMORY_SNAPSHOT = True

# GPU memory snapshot (ALPHA): also capture the CUDA/ONNX session in the snapshot.
# DISABLED — restoring an onnxruntime CUDA session from a GPU snapshot segfaults
# (SIGSEGV, exit 139), and the failed restore makes cold starts *worse* (~30s)
# before Modal falls back to a no-snapshot boot. Keep False; the CPU-only
# snapshot below gives a clean ~8.9s restored cold start.
ENABLE_GPU_SNAPSHOT = False

# Require Modal proxy-auth tokens on the web endpoints (replaces the nginx auth
# layer from the Docker deployment). Set False only for open/public endpoints.
REQUIRES_PROXY_AUTH = True

# Directory inside the image where baked-in models live; also the on-demand
# download cache for non-baked models (writable container overlay at runtime).
BAKED_CHECKPOINTS_DIR = "/models"

# Models baked into the image at build time for fast cold starts.
# Names are the model file stem without ".onnx" (e.g. "df_default_2.0.2" for
# df_default_2.0.2.onnx). Anything not listed still works via download-on-demand.
BAKED_MODELS: tuple[str, ...] = ("df_default_2.0.2",)

# Public Scaleway bucket → HTTPS, no credentials required.
# Layout is directory-style: models/{name}/model.onnx and models/{name}/spec.json.
MODEL_BUCKET = "daylight-factor"
MODEL_URL_TEMPLATE = f"https://{MODEL_BUCKET}.s3.fr-par.scw.cloud/models/{{name}}/model.onnx"
SPEC_URL_TEMPLATE = f"https://{MODEL_BUCKET}.s3.fr-par.scw.cloud/models/{{name}}/spec.json"

# Non-sensitive env injected into the containers, read by ServerBootstrap.from_env().
RUNTIME_ENV = {
    "MODEL_BUCKET": MODEL_BUCKET,
    "MODEL_URL_TEMPLATE": MODEL_URL_TEMPLATE,
    "SPEC_URL_TEMPLATE": SPEC_URL_TEMPLATE,
}

# URL template used to fetch the baked models at build time. Public HTTPS needs
# no credentials; an s3:// template requires the Secret below.
BUILD_MODEL_URL_TEMPLATE = MODEL_URL_TEMPLATE

# Name of a modal.Secret holding Scaleway credentials (SCW_ACCESS_KEY,
# SCW_SECRET_KEY). ONLY needed for a PRIVATE bucket (s3:// URLs). Leave None for
# the public HTTPS bucket above.
SECRET_NAME: Optional[str] = None
