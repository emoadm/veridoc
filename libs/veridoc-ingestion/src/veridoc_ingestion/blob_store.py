"""Provider-portable blob-store abstraction for retained original documents (D-10).

Mirrors the KMSKeyring pattern in veridoc-crypto/kms.py exactly:

  - :class:`BlobStore` — the ABC (mirrors ``KMSKeyring``).
  - :class:`S3BlobStore` — the working implementation (mirrors ``LocalKeyring``);
    uses boto3 and supports MinIO (via ``endpoint_url``) and real AWS S3.
  - :class:`AzureBlobStore` — Azure Blob Storage stub (mirrors ``AzureKeyVaultKeyring``);
    raises :exc:`NotImplementedError` until DEC-cloud-provider closes to Azure.

**Cloud portability (D-10):** ``S3BlobStore`` accepts an optional ``endpoint_url``
parameter.  Setting it routes all requests to a MinIO instance (local/CI).  Omitting it
targets real AWS S3.  No code change is required to switch between the two; only config
changes (remove ``VERIDOC_BLOB_ENDPOINT_URL`` in production).

**Object-key non-enumerability (T-02-BLOB-01):** Callers must supply UUID-based keys
that include the ``site_id`` prefix (e.g. ``f"{site_id}/{uuid4()}.{ext}"``).  The
``S3BlobStore`` does not validate key format — that is the adapter's responsibility —
but the blob-store contract documents the expectation.

**Bucket access (T-02-BLOB-02):** The bucket must have no public access; the boto3
client is always authenticated (``access_key`` / ``secret_key`` or IAM role ambient
credentials when both are empty strings).
"""

from __future__ import annotations

import abc

__all__ = ["BlobStore", "S3BlobStore", "AzureBlobStore"]


class BlobStore(abc.ABC):
    """Provider-portable blob store (mirrors KMSKeyring in veridoc-crypto; D-10).

    Implementations: S3BlobStore (MinIO + AWS S3), AzureBlobStore (stub).
    """

    @abc.abstractmethod
    def put(self, key: str, data: bytes, content_type: str) -> str:
        """Upload ``data`` under ``key``; return the object URI.

        Keys should be non-guessable (UUID + site_id prefix) to prevent enumeration
        attacks (T-02-BLOB-01).  The returned URI format is implementation-defined;
        :class:`S3BlobStore` returns ``s3://{bucket}/{key}``.

        Args:
            key: Object key (e.g. ``"site-001/3b1d…-original.tiff"``).
            data: Raw bytes to store (the retained original document).
            content_type: MIME type (e.g. ``"image/tiff"``, ``"application/pdf"``).

        Returns:
            A URI identifying the stored object.
        """

    @abc.abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve the bytes stored under ``key``.

        Args:
            key: Object key previously returned by :meth:`put`.

        Returns:
            The stored bytes, identical to what was passed to :meth:`put`.
        """


class S3BlobStore(BlobStore):
    """S3-compatible blob store. Works with MinIO (``endpoint_url``) and real AWS S3.

    Pass ``endpoint_url`` for local/CI MinIO; omit for production AWS S3.  No other
    code change is needed to switch between the two (D-10, DEC-cloud-provider OPEN).

    Args:
        bucket: S3 bucket name (must exist before :meth:`put` is called).
        endpoint_url: MinIO or other S3-compatible endpoint URL.
                      ``None`` (default) targets real AWS S3.
        access_key: AWS / MinIO access key.  Empty string uses IAM ambient credentials
                    (real S3 with instance role).
        secret_key: AWS / MinIO secret key.  Paired with ``access_key``.
    """

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        access_key: str = "",
        secret_key: str = "",
    ) -> None:
        import boto3

        self._bucket = bucket
        kwargs: dict = {}
        if endpoint_url:  # MinIO local/CI path (D-10)
            kwargs["endpoint_url"] = endpoint_url
        if access_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
        self._client = boto3.client("s3", **kwargs)

    def put(self, key: str, data: bytes, content_type: str) -> str:
        """Upload ``data`` to the configured bucket; return the ``s3://`` URI.

        Args:
            key: Non-guessable object key (T-02-BLOB-01).
            data: Raw bytes (the retained original document).
            content_type: MIME type for the stored object.

        Returns:
            ``f"s3://{bucket}/{key}"`` — the canonical URI for the stored object.
        """
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{self._bucket}/{key}"

    def get(self, key: str) -> bytes:
        """Retrieve stored bytes by key.

        Args:
            key: Object key previously returned by :meth:`put`.

        Returns:
            Bytes identical to those passed to :meth:`put`.
        """
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()


class AzureBlobStore(BlobStore):  # pragma: no cover - DEC-cloud-provider OPEN
    """Azure Blob Storage adapter (interface stub this phase; DEC-cloud-provider OPEN).

    When DEC-cloud-provider closes to Azure, this wires ``azure-storage-blob`` so
    document retention uses Azure Blob Storage instead of MinIO/S3, without any
    changes to the adapter or service layers (the portability contract of D-10).
    """

    def put(self, key: str, data: bytes, content_type: str) -> str:
        raise NotImplementedError(
            "AzureBlobStore is a portability stub; wire azure-storage-blob "
            "when DEC-cloud-provider closes to Azure"
        )

    def get(self, key: str) -> bytes:
        raise NotImplementedError(
            "AzureBlobStore is a portability stub; wire azure-storage-blob "
            "when DEC-cloud-provider closes to Azure"
        )
