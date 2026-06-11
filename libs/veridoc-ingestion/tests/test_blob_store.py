"""Tests for BlobStore ABC, S3BlobStore (MinIO-compatible), and AzureBlobStore stub.

MinIO integration tests use the ``minio_endpoint`` session fixture from conftest.py
(testcontainers-backed). They skip cleanly when Docker is unavailable.

RED phase: these tests are written before the implementation exists and MUST fail.
GREEN phase: implementation in blob_store.py makes them pass.
"""

from __future__ import annotations

import abc
import inspect
import uuid

import pytest


def test_blob_store_is_abstract() -> None:
    """BlobStore must be an abc.ABC with abstract put and get methods."""
    from veridoc_ingestion.blob_store import BlobStore

    assert issubclass(BlobStore, abc.ABC)
    with pytest.raises(TypeError):
        BlobStore()  # type: ignore[abstract]


def test_s3_blob_store_is_concrete_subclass() -> None:
    """S3BlobStore must be a subclass of BlobStore."""
    from veridoc_ingestion.blob_store import BlobStore, S3BlobStore

    assert issubclass(S3BlobStore, BlobStore)


def test_s3_blob_store_has_endpoint_url_parameter() -> None:
    """S3BlobStore must accept endpoint_url (MinIO-compatible, DEC-cloud-provider portable)."""
    from veridoc_ingestion.blob_store import S3BlobStore

    source = inspect.getsource(S3BlobStore)
    assert "endpoint_url" in source, (
        "S3BlobStore must contain 'endpoint_url' parameter for MinIO compatibility"
    )


def test_azure_blob_store_put_raises_not_implemented() -> None:
    """AzureBlobStore.put must raise NotImplementedError."""
    from veridoc_ingestion.blob_store import AzureBlobStore

    store = AzureBlobStore()
    with pytest.raises(NotImplementedError, match="wire"):
        store.put("key", b"data", "application/octet-stream")


def test_azure_blob_store_get_raises_not_implemented() -> None:
    """AzureBlobStore.get must raise NotImplementedError."""
    from veridoc_ingestion.blob_store import AzureBlobStore

    store = AzureBlobStore()
    with pytest.raises(NotImplementedError, match="wire"):
        store.get("key")


def test_azure_blob_store_conforms_to_blob_store() -> None:
    """AzureBlobStore must be a subclass of BlobStore."""
    from veridoc_ingestion.blob_store import AzureBlobStore, BlobStore

    assert issubclass(AzureBlobStore, BlobStore)


# ---------------------------------------------------------------------------------
# MinIO integration tests (require Docker via testcontainers or VERIDOC_TEST_MINIO_URL)
# ---------------------------------------------------------------------------------


def test_s3_blob_store_put_returns_s3_uri(minio_endpoint: str) -> None:
    """S3BlobStore.put returns an ``s3://`` URI."""
    import boto3

    from veridoc_ingestion.blob_store import S3BlobStore

    bucket = f"test-{uuid.uuid4().hex[:8]}"
    store = S3BlobStore(
        bucket=bucket,
        endpoint_url=minio_endpoint,
        access_key="minioadmin",
        secret_key="minioadmin",
    )

    # Create the bucket first
    client = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )
    client.create_bucket(Bucket=bucket)

    key = f"site-001/{uuid.uuid4()}.bin"
    uri = store.put(key, b"hello-blob", "application/octet-stream")

    assert uri == f"s3://{bucket}/{key}", f"Expected s3://{bucket}/{key}, got {uri!r}"


def test_s3_blob_store_round_trip(minio_endpoint: str) -> None:
    """S3BlobStore.put then get returns identical bytes (T-02-BLOB-01 non-enumerable keys)."""
    import boto3

    from veridoc_ingestion.blob_store import S3BlobStore

    bucket = f"test-{uuid.uuid4().hex[:8]}"
    payload = b"veridoc-original-doc-\x00\x01\xff"

    # UUID-based key (T-02-BLOB-01: non-guessable key)
    key = f"site-001/{uuid.uuid4()}.bin"

    store = S3BlobStore(
        bucket=bucket,
        endpoint_url=minio_endpoint,
        access_key="minioadmin",
        secret_key="minioadmin",
    )

    # Create bucket
    client = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )
    client.create_bucket(Bucket=bucket)

    uri = store.put(key, payload, "application/octet-stream")
    retrieved = store.get(key)

    assert retrieved == payload, "Round-trip bytes must be identical"
    assert uri.startswith("s3://"), f"URI must start with s3://, got {uri!r}"


def test_s3_blob_store_content_type_preserved(minio_endpoint: str) -> None:
    """S3BlobStore.put sets ContentType correctly on the uploaded object."""
    import boto3

    from veridoc_ingestion.blob_store import S3BlobStore

    bucket = f"test-{uuid.uuid4().hex[:8]}"
    key = f"site-001/{uuid.uuid4()}.png"
    content_type = "image/png"

    store = S3BlobStore(
        bucket=bucket,
        endpoint_url=minio_endpoint,
        access_key="minioadmin",
        secret_key="minioadmin",
    )
    client = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )
    client.create_bucket(Bucket=bucket)

    store.put(key, b"\x89PNG\r\n\x1a\n", content_type)
    head = client.head_object(Bucket=bucket, Key=key)
    assert head["ContentType"] == content_type
