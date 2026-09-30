"""Document upload (CON-001, SEC-003).

Runs the SEC-003 scan/type-check synchronously, before any storage write or `Document`
row is persisted -- a rejected upload never touches object storage and never creates a
row (`docs/03-domain/contract-compliance.md` step 1).
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.domain.constants import DocumentStatus
from app.contracts.infrastructure.document_scanner import (
    compute_content_hash,
    safe_storage_filename,
    validate_and_scan,
)
from app.contracts.infrastructure.models import Document
from app.contracts.infrastructure.repositories import DocumentRepository
from app.core.config import get_settings
from app.core.storage import StoragePort
from app.evidence.application.audit_service import emit_audit_event


async def upload_document(
    session: AsyncSession,
    *,
    storage: StoragePort,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    filename: str,
    data: bytes,
) -> Document:
    """SEC-003 gate first (raises `FileTooLargeError`/`MalwareDetectedError`/
    `UnsupportedFileTypeError` -- the API layer maps these to 4xx); only a file that
    clears it ever becomes a `Document` row or an object-storage write."""
    settings = get_settings()
    sniffed_mime = validate_and_scan(
        data, filename=filename, max_size_bytes=settings.document_max_size_bytes
    )
    content_hash = compute_content_hash(data)

    document_id = uuid.uuid4()
    # Security review (2026-09-29): the storage key's filename component must never be
    # the raw client-supplied `filename` (see `safe_storage_filename`'s docstring) --
    # `original_filename` below keeps the raw value for display.
    storage_key = f"contracts/{organization_id}/{document_id}/{safe_storage_filename(filename)}"
    storage.put(storage_key, data, content_type=sniffed_mime)

    document = Document(
        id=document_id,
        organization_id=organization_id,
        uploaded_by=actor_id,
        original_filename=filename,
        storage_key=storage_key,
        content_hash=content_hash,
        mime_type=sniffed_mime,
        size_bytes=len(data),
        # The scan above already cleared before this row is even constructed, so the
        # Document is created directly in `processed` state -- there is no in-between
        # "scanning" persistence state in this design (contract-compliance.md's
        # `document.uploaded` / `document.processed` events fire back-to-back below).
        status=DocumentStatus.PROCESSED.value,
    )
    DocumentRepository(session).add(document)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="document.uploaded",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "document_id": str(document.id),
            "filename": filename,
            "mime_type": sniffed_mime,
            "content_hash": content_hash,
            "size_bytes": document.size_bytes,
        },
    )
    await emit_audit_event(
        session,
        event_type="document.processed",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={"document_id": str(document.id)},
    )

    return document
