"""Build-time helpers for the Modal image.

Kept separate from image.py so Modal can import and run these functions remotely
during the image build without re-executing the App/Image definition.

Imports of heavy deps (boto3, requests, onnxruntime) are deferred into the
functions on purpose: these packages exist in the build image but not
necessarily on the machine running `modal deploy`, which imports this module
locally to register the build steps.
"""
import os
from pathlib import Path
from typing import Sequence


def _download_s3(url: str, dest: Path) -> None:
    import boto3

    without_scheme = url[len("s3://"):]
    bucket, _, key = without_scheme.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URL — expected s3://bucket/key, got: {url!r}")
    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("SCW_ENDPOINT_URL", "https://s3.fr-par.scw.cloud"),
        aws_access_key_id=os.environ["SCW_ACCESS_KEY"],
        aws_secret_access_key=os.environ["SCW_SECRET_KEY"],
        region_name=os.getenv("SCW_REGION", "fr-par"),
    )
    s3.download_file(bucket, key, str(dest))


def _download_http(url: str, dest: Path) -> None:
    import requests

    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def download_baked_models(
    model_names: Sequence[str],
    url_template: str,
    dest_dir: str,
) -> None:
    """Download each model into dest_dir during the image build.

    Runs inside the build container; a failure aborts the build so a broken
    image is never published.
    """
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    for name in model_names:
        url = url_template.format(name=name)
        dest = Path(dest_dir) / f"{name}.onnx"
        print(f"[build] baking model '{name}' from {url}")
        if url.startswith("s3://"):
            _download_s3(url, dest)
        else:
            _download_http(url, dest)
        print(f"[build] wrote {dest} ({dest.stat().st_size / 1e6:.1f} MB)")


def optimize_baked_models(model_names: Sequence[str], dest_dir: str) -> None:
    """Pre-build the optimized ONNX graph for each baked model.

    Creating a session with ORT_ENABLE_ALL and `optimized_model_filepath` set
    writes the fully-optimized graph to disk ({name}.opt.onnx). At runtime that
    graph is loaded with optimizations disabled, so session init skips the graph
    transformation passes. The CUDA memory transfer at inference is unaffected.

    Runs with a GPU so the saved graph targets CUDAExecutionProvider — the same
    provider used at runtime. The optimized graph is hardware-specific and must
    be regenerated if the runtime GPU class changes.
    """
    import onnxruntime as ort

    providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
                 if p in ort.get_available_providers()]
    print(f"[build] optimizing with providers: {providers}")
    for name in model_names:
        src = Path(dest_dir) / f"{name}.onnx"
        optimized = Path(dest_dir) / f"{name}.opt.onnx"
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_options.optimized_model_filepath = str(optimized)
        # Session creation triggers optimization and writes optimized_model_filepath.
        ort.InferenceSession(str(src), sess_options=session_options, providers=providers)
        print(f"[build] wrote optimized graph {optimized} ({optimized.stat().st_size / 1e6:.1f} MB)")
