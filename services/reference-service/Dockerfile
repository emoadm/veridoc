# syntax=docker/dockerfile:1
#
# VeriDoc reference service — multi-stage image (plan 01-05; built/run in CI, plan 01-06).
#
# Stage 1 (builder): install uv, sync ONLY the reference-service workspace member plus its
#   five veridoc_* lib dependencies into a self-contained virtualenv.
# Stage 2 (runtime): a slim python base with NO build toolchain, the prebuilt venv copied in,
#   a non-root user, and uvicorn launching reference_service.main:app.
#
# Security (T-05-02): NO secrets are baked into the image. All configuration — DB URL,
# Keycloak issuer/JWKS/audience, Redis URL, KMS/master-key — arrives from environment
# variables / Kubernetes Secrets at runtime (plan 01-06). Do not add ENV/ARG secrets here.

# --- Stage 1: builder -------------------------------------------------------------------
FROM python:3.12-slim AS builder

# uv is the workspace package manager (D-08). Pin a known-good release for reproducibility.
COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy the workspace manifests + lockfile first so dependency resolution is cached across
# source-only changes. The reference service resolves its five libs as workspace members.
COPY pyproject.toml uv.lock ./
COPY libs/ ./libs/
COPY services/reference-service/pyproject.toml ./services/reference-service/

# Sync only the reference-service member (and the workspace libs it depends on), no dev deps.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package reference-service --no-install-project

# Now copy the actual source and install the project itself into the venv.
COPY services/reference-service/ ./services/reference-service/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package reference-service

# --- Stage 2: runtime -------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Create a non-root user to run the service (least privilege; no root in the container).
RUN groupadd --system --gid 1001 veridoc \
    && useradd --system --uid 1001 --gid 1001 --no-create-home --shell /usr/sbin/nologin veridoc

WORKDIR /app

# Copy the prebuilt virtualenv and the service source from the builder (no toolchain here).
COPY --from=builder --chown=veridoc:veridoc /app/.venv /app/.venv
COPY --from=builder --chown=veridoc:veridoc /app/services/reference-service /app/services/reference-service
COPY --from=builder --chown=veridoc:veridoc /app/libs /app/libs

# Put the venv on PATH so `uvicorn` resolves to the synced one.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER veridoc

# Launch the ASGI app. Config (DB/Keycloak/Redis/KMS) is injected via env at runtime.
CMD ["uvicorn", "reference_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
