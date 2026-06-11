# syntax=docker/dockerfile:1
#
# VeriDoc ingestion service — multi-stage image (plan 02-06).
#
# Cloned from services/reference-service/Dockerfile and extended with:
#   - Tesseract OCR system package in BOTH builder and runtime stages (Pitfall 8 /
#     T-02-SVC-05: TesseractNotFoundError eliminated at runtime).
#   - Supports two container roles from one image:
#       API server (default CMD): uvicorn ingestion_service.main:app
#       RQ worker (override CMD): rq worker ingestion --serializer ...
#
# Security (T-05-02): NO secrets baked into the image. All configuration — DB/Mongo/
# Redis/Keycloak/blob — arrives from environment variables / Kubernetes Secrets at runtime.

# --- Stage 1: builder -------------------------------------------------------------------
FROM python:3.12-slim AS builder

# uv is the workspace package manager (D-08). Pin a known-good release for reproducibility.
COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install Tesseract OCR in the builder stage (Pitfall 8 guard / T-02-SVC-05).
# Required so pytesseract can invoke the system binary during image build verification.
# Both builder and runtime stages install it so the binary is present in the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy the workspace manifests + lockfile first so dependency resolution is cached across
# source-only changes. The ingestion-service resolves its veridoc libs as workspace members.
COPY pyproject.toml uv.lock ./
COPY libs/ ./libs/
COPY services/ingestion-service/pyproject.toml ./services/ingestion-service/

# Sync only the ingestion-service member (and the workspace libs it depends on), no dev deps.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package ingestion-service --no-install-project

# Now copy the actual source and install the project itself into the venv.
COPY services/ingestion-service/ ./services/ingestion-service/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package ingestion-service

# --- Stage 2: runtime -------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Create a non-root user to run the service (least privilege; no root in the container).
RUN groupadd --system --gid 1001 veridoc \
    && useradd --system --uid 1001 --gid 1001 --no-create-home --shell /usr/sbin/nologin veridoc

# Install Tesseract OCR in the runtime stage (Pitfall 8 guard / T-02-SVC-05).
# pytesseract requires the system binary at RUNTIME — it is not embedded in the venv.
# Installing in BOTH stages (builder above, runtime here) ensures the binary is always
# present regardless of which stage is inspected or executed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the prebuilt virtualenv and the service source from the builder (no toolchain here).
COPY --from=builder --chown=veridoc:veridoc /app/.venv /app/.venv
COPY --from=builder --chown=veridoc:veridoc /app/services/ingestion-service /app/services/ingestion-service
COPY --from=builder --chown=veridoc:veridoc /app/libs /app/libs

# Put the venv on PATH so uvicorn/rq resolve to the synced one.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER veridoc

# Default CMD: API server (uvicorn).
# Worker override (K8s Deployment command):
#   rq worker ingestion --serializer rq.serializers.JSONSerializer --url $VERIDOC_REDIS_URL
CMD ["uvicorn", "ingestion_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
