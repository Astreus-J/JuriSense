"""Storage abstraction smoke test (STORY-1.3.1 / ADR-008).

Unlike the Redis/DB fixtures (`fakeredis`, in-memory `aiosqlite` -- see
`tests/conftest.py`), this project has no in-memory substitute for the S3 API
as faithful as those two libraries are for their respective protocols. Adding
a dependency just to simulate S3 (e.g. `moto`) would trade a mature, widely
used reimplementation of the real API for a simulation -- and this smoke
test's whole point is to validate the real S3-compatible backend's behavior
(s3mock's S3 emulation today, Cloudflare R2 in production), not an
approximation of it. So this test runs against a real s3mock instance,
and skips with a clear reason when the service is unreachable -- the expected
case in this sandboxed environment, but not under `docker compose up -d`.
"""

from uuid import uuid4

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from app.core.config import get_settings
from app.core.storage import S3CompatibleStorage


@pytest.fixture
def storage() -> S3CompatibleStorage:
    settings = get_settings()
    adapter = S3CompatibleStorage(
        endpoint_url=settings.storage_endpoint_url,
        access_key=settings.storage_access_key,
        secret_key=settings.storage_secret_key,
        bucket=settings.storage_bucket,
        region=settings.storage_region,
    )

    try:
        adapter._client.create_bucket(Bucket=settings.storage_bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise
    except (EndpointConnectionError, ConnectionError) as exc:
        pytest.skip(
            f"s3mock is not reachable at {settings.storage_endpoint_url} "
            f"(run `docker compose up -d s3mock` to exercise this test): {exc}"
        )

    return adapter


def test_put_and_get_roundtrip(storage: S3CompatibleStorage) -> None:
    key = f"smoke-tests/{uuid4()}.txt"
    content = b"storage smoke test content"

    storage.put(key, content, content_type="text/plain")
    try:
        assert storage.get(key) == content
    finally:
        storage._client.delete_object(Bucket=storage._bucket, Key=key)


def test_generate_presigned_url_roundtrip(storage: S3CompatibleStorage) -> None:
    key = f"smoke-tests/{uuid4()}.txt"
    storage.put(key, b"content", content_type="text/plain")
    try:
        url = storage.generate_presigned_url(key, expires_in=60)
        assert storage._bucket in url
        assert key in url
    finally:
        storage._client.delete_object(Bucket=storage._bucket, Key=key)
