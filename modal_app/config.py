"""Configuration constants for the Modal deployment.

Centralizes every tunable value (GPU type, baked models, scaling, auth, URLs)
so the app/image modules contain no magic strings.
"""
import os
from typing import Optional

# Modal app name (shown in the dashboard and in deployed endpoint URLs).
APP_NAME = "upskiller-model"

# Env var (deploy-time, comma-separated) overriding ALLOWED_MODELS without a code
# change. Resolved here and baked into the container env via RUNTIME_ENV so the
# in-container re-import sees the same value.
ALLOWED_MODELS_ENV = "ALLOWED_MODELS"

# GPU class for the inference container.
GPU = "L4"

# Seconds a warm container is kept alive after its last request (cold-start vs cost).
# 60s: scale to zero quickly to minimise idle cost; trades more frequent cold starts
# (mitigated by the /warm prewarm path) for a shorter idle tail.
SCALEDOWN_WINDOW = 60

# Containers kept permanently warm. 0 = scale to zero (cheapest, cold starts).
MIN_CONTAINERS = 0

# Hard ceiling on horizontal scale-out (defense-in-depth, not perf). Proxy-auth is
# the gate; this caps the blast radius / GPU spend if a token leaks or an authorized
# caller floods /run — Modal will not boot more than this many GPU containers no
# matter how much authorized traffic arrives. The serverless-correct equivalent of
# rate limiting (in-memory per-container limits are unreliable across autoscaling).
MAX_CONTAINERS = 4

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

# Max accepted request body size. /run reads the whole upload into memory on a GPU
# container, so an oversized payload (from a buggy or compromised authorized caller)
# could OOM the container or waste GPU time. Requests advertising more than this via
# Content-Length are rejected with 413 before the body is read. 25 MB comfortably
# covers expected images while blocking multi-hundred-MB payloads.
MAX_REQUEST_BYTES = 25 * 1024 * 1024

# Models this deployment is willing to serve. /run and /spec fetch by model name and
# fall back to download-on-demand, so an unrestricted name lets a caller trigger
# arbitrary registry fetches. Names not listed here are rejected with 400.
# Override per deploy by setting the ALLOWED_MODELS env var (comma-separated);
# otherwise the default below applies. Download-on-demand still works for permitted
# names — the allowlist only gates which names are accepted.
_DEFAULT_ALLOWED_MODELS: tuple[str, ...] = (
    "df_default",
    "df_default_2.0.1",
    "df_default_2.0.2",
)


def _parse_allowed_models(raw: Optional[str]) -> tuple[str, ...]:
    """Parse the comma-separated ALLOWED_MODELS env var, falling back to default."""
    if not raw:
        return _DEFAULT_ALLOWED_MODELS
    names = tuple(name.strip() for name in raw.split(",") if name.strip())
    return names or _DEFAULT_ALLOWED_MODELS


ALLOWED_MODELS: tuple[str, ...] = _parse_allowed_models(os.getenv(ALLOWED_MODELS_ENV))

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
    # Bake the resolved allowlist into the container so the in-container import of
    # this module parses the same value the deploy resolved (env is not otherwise
    # carried into the container).
    ALLOWED_MODELS_ENV: ",".join(ALLOWED_MODELS),
}

# URL template used to fetch the baked models at build time. Public HTTPS needs
# no credentials; an s3:// template requires the Secret below.
BUILD_MODEL_URL_TEMPLATE = MODEL_URL_TEMPLATE

# Name of a modal.Secret holding Scaleway credentials (SCW_ACCESS_KEY,
# SCW_SECRET_KEY). ONLY needed for a PRIVATE bucket (s3:// URLs). Leave None for
# the public HTTPS bucket above.
SECRET_NAME: Optional[str] = None
