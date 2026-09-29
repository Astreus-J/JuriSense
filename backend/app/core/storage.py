"""Object storage abstraction (ADR-008).

A single port (`StoragePort`) used by any bounded context that needs to
read/write files (today none -- `Contracts & Documents` and `Evidence &
Audit` are future work). The concrete adapter speaks the S3 API and works
unmodified against s3mock's S3 emulation (development) or Cloudflare R2
(production): both are S3-compatible, so swapping backends is only a matter
of changing credentials/endpoint in `Settings`, never the application code.
See ADR-008 (and its addendum: MinIO, the original dev choice, no longer
publishes a freely pullable image, hence s3mock).
"""

from functools import lru_cache
from typing import Annotated, Protocol

import boto3
from botocore.client import Config as BotoConfig
from fastapi import Depends

from app.core.config import get_settings


class StoragePort(Protocol):
    """Storage port any bounded context can depend on."""

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Write (or overwrite) an object under `key`."""
        ...

    def get(self, key: str) -> bytes:
        """Read an object's content. Raises if `key` does not exist."""
        ...

    def generate_presigned_url(self, key: str, expires_in: int) -> str:
        """Generate a temporary URL (valid for `expires_in` seconds) for `key`."""
        ...


class S3CompatibleStorage:
    """The single concrete adapter: speaks S3 via boto3.

    Serves both s3mock's S3 emulation (dev) and Cloudflare R2 (production)
    with no code change -- only `endpoint_url`/credentials change per
    environment (see `Settings.storage_*` in `app/core/config.py` and the
    `s3mock` service in `docker-compose.yml`).
    """

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=BotoConfig(signature_version="s3v4"),
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def generate_presigned_url(self, key: str, expires_in: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )


@lru_cache
def get_storage() -> StoragePort:
    settings = get_settings()
    return S3CompatibleStorage(
        endpoint_url=settings.storage_endpoint_url,
        access_key=settings.storage_access_key,
        secret_key=settings.storage_secret_key,
        bucket=settings.storage_bucket,
        region=settings.storage_region,
    )


StorageDep = Annotated[StoragePort, Depends(get_storage)]
