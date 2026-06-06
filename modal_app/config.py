"""Configuration constants for the Modal deployment.

Centralizes every tunable value (GPU type, baked models, scaling, auth) so the
app/image modules contain no magic strings.
"""

# Modal app name (shown in the dashboard and in deployed endpoint URLs).
APP_NAME = "upskiller-model"

# Name of the modal.Secret holding Scaleway S3 credentials and URL templates.
# Expected keys: SCW_ACCESS_KEY, SCW_SECRET_KEY, MODEL_URL_TEMPLATE,
# SPEC_URL_TEMPLATE (and optionally SCW_REGION, SCW_ENDPOINT_URL, MODEL_BUCKET).
SECRET_NAME = "upskiller-scaleway"

# GPU class for the inference container.
GPU = "L4"

# Seconds a warm container is kept alive after its last request (cold-start vs cost).
SCALEDOWN_WINDOW = 300

# Containers kept permanently warm. 0 = scale to zero (cheapest, cold starts).
MIN_CONTAINERS = 0

# Require Modal proxy-auth tokens on the web endpoints (replaces the nginx auth
# layer from the Docker deployment). Set False only for open/public endpoints.
REQUIRES_PROXY_AUTH = True

# Directory inside the image where baked-in models live; also the on-demand
# download cache for non-baked models (writable container overlay at runtime).
BAKED_CHECKPOINTS_DIR = "/models"

# Models baked into the image at build time for fast cold starts.
# TODO(user): fill in the model names to bake, e.g. ("df_default_2.0.1",).
# Anything not listed here still works via download-on-demand from Scaleway.
BAKED_MODELS: tuple[str, ...] = ()

# URL template used at BUILD time to fetch the baked models. Runtime download of
# non-baked models is driven separately by the MODEL_URL_TEMPLATE env var (from
# the Secret). s3:// uses the credentials in the Secret; https:// is public.
BUILD_MODEL_URL_TEMPLATE = "s3://daylight-factor/models/{name}.onnx"
