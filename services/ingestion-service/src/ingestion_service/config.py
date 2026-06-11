"""Ingestion-service configuration (pydantic-settings).

All runtime configuration is sourced from the environment (12-factor / T-05-02: no
secrets baked into the image — config arrives from K8s Secrets/env at runtime).
The Keycloak issuer/JWKS/audience anchor token verification; the DB URL anchors
Postgres (audit); the Mongo URL anchors the FHIR document store (D-02); blob config
anchors the retained-original store (D-10).

Cloned from ``services/reference-service/src/reference_service/config.py`` (exact
analog) with five new fields for MongoDB and blob store (02-PATTERNS.md).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ingestion-service settings (env-sourced, prefix ``VERIDOC_``)."""

    model_config = SettingsConfigDict(env_prefix="VERIDOC_", extra="ignore")

    # Persistence — Postgres (audit chain, D-05)
    database_url: str = Field(
        default="postgresql+psycopg://localhost/veridoc",
        description="SQLAlchemy URL for the service Postgres (psycopg v3 driver).",
    )

    # Redis — RQ job queue (D-06)
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Keycloak / OIDC (D-01/D-02). The issuer + JWKS URI + audience anchor token trust.
    keycloak_issuer: str = Field(
        default="https://kc.veridoc.local/realms/veridoc",
        description="OIDC issuer (Keycloak realm URL); tokens must carry this iss.",
    )
    keycloak_jwks_uri: str = Field(
        default="https://kc.veridoc.local/realms/veridoc/protocol/openid-connect/certs",
        description="JWKS endpoint for RS256 signature verification.",
    )
    keycloak_audience: str = Field(
        default="ingestion-service",
        description="Expected token audience (the ingestion-service OIDC client).",
    )
    keycloak_client_id: str = Field(default="ingestion-service")

    # KMS / master key for the per-patient key hierarchy (veridoc-crypto).
    kms_master_key_uri: str = Field(default="local://dev-master-key")

    # MongoDB — FHIR document store (D-02, DEC-pymongo-asyncclient)
    mongodb_url: str = Field(
        default="mongodb://localhost:27017/veridoc_fhir",
        description="AsyncMongoClient URL for the FHIR document store (D-02).",
    )

    # Blob store — retained originals (D-10, DEC-cloud-provider OPEN)
    blob_endpoint_url: str | None = Field(
        default=None,
        description=(
            "S3-compatible endpoint URL; None = real AWS S3; "
            "set to MinIO URL for local/CI (D-10)."
        ),
    )
    blob_bucket: str = Field(
        default="veridoc-docs",
        description="S3/MinIO bucket name for retained original documents.",
    )
    blob_access_key: str = Field(default="")
    blob_secret_key: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (constructed once per process)."""
    return Settings()
