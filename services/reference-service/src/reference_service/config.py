"""Reference-service configuration (pydantic-settings).

All runtime configuration is sourced from the environment (12-factor / T-05-02: no secrets
baked into the image — config arrives from K8s Secrets/env at runtime, plan 01-06). The
Keycloak issuer/JWKS/audience anchor token verification; the DB URL anchors persistence;
the master-key/KMS config anchors the per-patient key hierarchy (veridoc-crypto sources the
master key from ``VERIDOC_MASTER_KEY`` / the KMS abstraction).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reference-service settings (env-sourced, prefix ``VERIDOC_``)."""

    model_config = SettingsConfigDict(env_prefix="VERIDOC_", extra="ignore")

    # Persistence.
    database_url: str = Field(
        default="postgresql+psycopg://localhost/veridoc",
        description="SQLAlchemy URL for the service Postgres (psycopg v3 driver).",
    )

    # Session store (D-10) — wired by later phases; declared for config completeness.
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
        default="reference-service",
        description="Expected token audience (the reference-service OIDC client).",
    )
    keycloak_client_id: str = Field(default="reference-service")

    # KMS / master key for the per-patient key hierarchy (veridoc-crypto). The master key is
    # read by veridoc_crypto.keys.load_master_key() from VERIDOC_MASTER_KEY; in production it
    # is wrapped by the cloud KMS (DEC-cloud-provider OPEN). No plaintext key in the image.
    kms_master_key_uri: str = Field(default="local://dev-master-key")


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (constructed once per process)."""
    return Settings()
