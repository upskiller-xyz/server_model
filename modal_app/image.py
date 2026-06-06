"""Modal image and shared resources (Secret) for the deployment.

The image installs the GPU ONNX runtime stack, bakes the configured models in
at build time, then mounts the application source for runtime use.
"""
import modal

from . import config
from .build import download_baked_models, optimize_baked_models

# Scaleway credentials + URL templates, injected as environment variables into
# both the build step and the running containers.
scaleway_secret = modal.Secret.from_name(config.SECRET_NAME)

image = (
    modal.Image.debian_slim(python_version="3.11")
    # OpenCV runtime libs (mirrors the Docker base).
    .apt_install("libgl1", "libglib2.0-0", "libgomp1")
    .pip_install_from_requirements("requirements.modal.txt")
    # Bake the configured models into BAKED_CHECKPOINTS_DIR at build time.
    .run_function(
        download_baked_models,
        args=(
            list(config.BAKED_MODELS),
            config.BUILD_MODEL_URL_TEMPLATE,
            config.BAKED_CHECKPOINTS_DIR,
        ),
        secrets=[scaleway_secret],
    )
    # Pre-build the optimized graph on a GPU so it targets CUDAExecutionProvider.
    .run_function(
        optimize_baked_models,
        args=(list(config.BAKED_MODELS), config.BAKED_CHECKPOINTS_DIR),
        gpu=config.GPU,
    )
    # Application source, available at runtime inside the container.
    .add_local_python_source("src", "modal_app")
)
