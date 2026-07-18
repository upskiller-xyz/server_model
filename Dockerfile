# ONNX Model Server - Production Dockerfile
FROM python:3.11-slim

# Install system dependencies for OpenCV and PyTorch
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker cache
COPY requirements.txt .

# Pinned build-tooling versions keep the image reproducible; override with
# --build-arg if a newer patched release is needed. These floors clear the
# pip / setuptools / wheel CVE scan findings (setuptools 83 also vendors the
# patched jaraco.context 6.1 + wheel 0.46.3 under setuptools/_vendor/).
ARG PIP_VERSION=26.1.2
ARG SETUPTOOLS_VERSION=83.0.0
ARG WHEEL_VERSION=0.47.0
# Upgrade build tooling (fixes pip / setuptools / wheel CVEs) and install deps.
# The installs stay &&-gated so any failure fails the build; the final cleanup
# purges the old bundled/cached wheels the base image ships (ensurepip stashes
# vulnerable .whl files that scanners still flag even after an upgrade) in a
# best-effort block so every step runs regardless of the others' exit codes.
RUN pip install --no-cache-dir --upgrade "pip==${PIP_VERSION}" "setuptools==${SETUPTOOLS_VERSION}" "wheel==${WHEEL_VERSION}" && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    { \
        find /usr/local/lib -type d -name "_bundled" -path "*ensurepip*" -exec rm -rf {} + 2>/dev/null; \
        rm -rf /root/.cache/pip; \
    }

# Copy source code
COPY src/ ./src/
COPY main.py .

# Create checkpoints directory for model cache
RUN mkdir -p /app/checkpoints

# Set file permissions (read-only for security)
RUN chmod 444 main.py
RUN chmod 444 requirements.txt

# Environment variables
ENV PORT=8083
ENV MODEL=df_default_2.0.1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/')" || exit 1

# Run with gunicorn
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 900 --access-logfile - --error-logfile - main:app"]
