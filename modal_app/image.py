"""Modal image and shared resources for the deployment.

The image installs the GPU ONNX runtime stack, sets the non-sensitive runtime
env, bakes the configured models in at build time (download + ORT optimization),
then mounts the application source for runtime use.
"""
import modal

from . import config
from .build import download_baked_models, optimize_baked_models

# Scaleway credentials, only for a private bucket. Empty for the public HTTPS
# bucket. Attached to both the build download step and the runtime containers.
runtime_secrets = (
    [modal.Secret.from_name(config.SECRET_NAME)] if config.SECRET_NAME else []
)

image = (
    # CUDA base image: onnxruntime-gpu needs the CUDA 12 / cuDNN 9 shared libs
    # (libcublasLt.so.12 etc.) which debian_slim lacks. Tag matches ORT's CUDA
    # 12.x + cuDNN 9.x requirement for onnxruntime-gpu 1.20–1.26 (the cap pinned in
    # requirements.modal.txt; 1.27+ moved to CUDA 13 and needs a CUDA 13 base).
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04",
        add_python="3.11",
    )
    # OpenCV runtime libs.
    .apt_install("libgl1", "libglib2.0-0", "libgomp1")
    .pip_install_from_requirements("requirements.modal.txt")
    # Non-sensitive config read by ServerBootstrap.from_env() at runtime.
    .env(config.RUNTIME_ENV)
    # Bake the configured models into BAKED_CHECKPOINTS_DIR at build time.
    .run_function(
        download_baked_models,
        args=(
            list(config.BAKED_MODELS),
            config.BUILD_MODEL_URL_TEMPLATE,
            config.BAKED_CHECKPOINTS_DIR,
        ),
        secrets=runtime_secrets,
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
