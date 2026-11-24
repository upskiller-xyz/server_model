# ONNX Model Server - Production Dockerfile (CPU image)
#
# Project Hummingbird (Red Hat hardened, distroless Python). Two stages: the
# -builder image (has pip and a shell) builds a venv, and the distroless runtime
# image (no shell, no package manager, runs as UID 65532) only receives the venv
# and the source. Both are pinned by index digest (multi-arch); bump tag and
# digest together:
#   docker buildx imagetools inspect registry.access.redhat.com/hi/python:3.14
#   docker buildx imagetools inspect registry.access.redhat.com/hi/python:3.14-builder
#
# No OS packages are installed: OpenCV is the headless wheel, which needs no
# libGL/libX*, and the wheels (onnxruntime, numpy, opencv) bundle the native
# libraries they need. Modal does not use this file; it has its own image
# definition in modal_app/image.py.

FROM registry.access.redhat.com/hi/python:3.15-builder@sha256:f0f26eaca78fb6e4a489640ab7578ea1022120ed044f31f575961f9935d102a9 AS build

# The builder image runs as 65532 too; installing into /opt needs root.
USER 0
RUN python3 -m venv /opt/venv
# pip is removed from the venv afterwards: nothing runs it at runtime, and it
# would only add scan findings.
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
    && /opt/venv/bin/pip uninstall --yes pip \
    && mkdir -p /out/checkpoints

FROM registry.access.redhat.com/hi/python:3.15@sha256:0766d2d64024695dc2cb90d251c247b834d5ea8b3dec28134f09e47ff6ad68a0

WORKDIR /app
# HOME is /tmp in the base image already; stated so the boto3/onnxruntime
# lookups under ~ cannot land on a read-only path after a base-image change.
ENV PATH=/opt/venv/bin:$PATH \
    HOME=/tmp \
    PORT=8083 \
    MODEL=df_default_2.0.1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY --from=build /opt/venv /opt/venv
# Source is root-owned, read-only for the app user.
COPY src/ ./src/
COPY main.py .
# The model download cache (./checkpoints, relative to /app) is the only path
# the app writes. Owned by the runtime user so a named volume mounted there
# inherits that ownership.
COPY --from=build --chown=65532:65532 /out/checkpoints /app/checkpoints

EXPOSE 8083

# Exec form: the runtime image has no shell. Any HTTP error fails the check.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://localhost:%s/' % os.environ['PORT'], timeout=5)"]

# The image default (65532), stated explicitly so a base-image change cannot
# silently make the server run as root.
USER 65532

# No --bind: with PORT set, gunicorn binds 0.0.0.0:$PORT by default. Exec form
# does no variable expansion, so this is how $PORT is honoured without a shell.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--timeout", "900", "--access-logfile", "-", "--error-logfile", "-", "main:app"]
