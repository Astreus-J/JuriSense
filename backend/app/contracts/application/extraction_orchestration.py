"""Runs AI structured extraction for one `ContractVersion` (CON-003, AI-001..003) and
applies the BR-CON-003 confidence gate. Mirrors
`app.suppliers.application.check_service`'s split: `trigger_extraction` only creates the
enqueue-able state and hands off to Celery; `run_extraction_for_version` is the actual
work, invoked by the Celery task in production and directly (against the test database)
by tests via the `enqueue_contract_extraction` seam.

Boundary rule (AI-004, `docs/04-architecture/components.md` rule 4): this module calls
`app.ai_services.application.extraction_service` (an application-layer function call,
never `app.ai_services.infrastructure` directly) and writes the DTO it gets back into
`Contracts & Documents`' own tables itself -- `AI Services` never touches
`ContractVersion`/`Clause` rows.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_services.application.extraction_service import run_contract_extraction
from app.ai_services.domain.errors import AllProvidersExhaustedError, DocumentParsingError
from app.contracts.domain.constants import ContractVersionStatus, DocumentStatus
from app.contracts.domain.errors import ContractVersionNotFoundError, DocumentNotFoundError
from app.contracts.domain.extracted_data import min_confidence
from app.contracts.infrastructure.models import Clause, ContractVersion, Document
from app.contracts.infrastructure.repositories import ClauseRepository, ContractVersionRepository
from app.core.config import get_settings
from app.core.storage import get_storage
from app.evidence.application.audit_service import emit_audit_event

logger = logging.getLogger("jurisense.contracts.extraction")


async def trigger_extraction(session: AsyncSession, *, contract_version: ContractVersion) -> None:
    """Committed before enqueueing (mirrors `check_service.trigger_check`) so the worker
    (its own session) can already see the `ContractVersion` row."""
    await session.commit()
    await enqueue_contract_extraction(contract_version.id)


async def enqueue_contract_extraction(contract_version_id: uuid.UUID) -> None:
    """The one seam tests monkeypatch (module-qualified -- see
    `check_service.enqueue_supplier_check`'s docstring for why) to run extraction
    synchronously against the test database instead of a real Celery worker."""
    from app.contracts.infrastructure.tasks import run_contract_extraction_task

    run_contract_extraction_task.delay(str(contract_version_id))


async def _fail_version(
    session: AsyncSession,
    *,
    version: ContractVersion,
    document: Document,
    reason: str,
) -> None:
    version.status = ContractVersionStatus.EXTRACTION_FAILED.value
    version.extraction_failure_reason = reason
    document.status = DocumentStatus.PROCESSING_FAILED.value
    document.failure_reason = reason
    await emit_audit_event(
        session,
        event_type="document.processing_failed",
        actor_id=None,
        organization_id=document.organization_id,
        payload={
            "document_id": str(document.id),
            "contract_version_id": str(version.id),
            "reason": reason,
        },
    )
    await session.commit()
    logger.warning("ContractVersion %s extraction failed: %s", version.id, reason)


async def run_extraction_for_version(
    session: AsyncSession, *, contract_version_id: uuid.UUID
) -> ContractVersion:
    version_repo = ContractVersionRepository(session)
    version = await version_repo.get_by_id(contract_version_id)
    if version is None:
        raise ContractVersionNotFoundError()

    document = await session.get(Document, version.document_id)
    if document is None:
        raise DocumentNotFoundError()

    storage = get_storage()
    document_bytes = storage.get(document.storage_key)

    try:
        envelope = await run_contract_extraction(
            document_id=str(document.id),
            contract_version_id=str(version.id),
            document_bytes=document_bytes,
            mime_type=document.mime_type,
        )
    except DocumentParsingError as exc:
        await _fail_version(session, version=version, document=document, reason=str(exc))
        return version
    except AllProvidersExhaustedError as exc:
        # Security review (2026-09-29): `exc.message` includes each attempt's raw
        # upstream response text (`openrouter_gateway.py`'s `response.text[:500]`) --
        # useful for debugging, but this is minor vendor-internals information
        # disclosure once it reaches `extraction_failure_reason`, which the API returns
        # verbatim to any org member. Full detail goes to the log only; the persisted/
        # API-exposed reason stays generic.
        logger.warning(
            "ContractVersion %s: all AI Gateway providers exhausted -- %s",
            version.id,
            exc.message,
        )
        await _fail_version(
            session,
            version=version,
            document=document,
            reason="AI extraction failed after trying all configured providers/models",
        )
        return version

    fields_dict = envelope.fields.model_dump(mode="json")
    confidence = min_confidence(fields_dict)
    settings = get_settings()

    version.extracted_data = {
        "extraction_run_id": envelope.extraction_run_id,
        "model": envelope.model.model_dump(mode="json"),
        "extracted_at": envelope.extracted_at,
        "pagination_mode": envelope.pagination_mode,
        "fields": fields_dict,
    }
    version.extraction_confidence = confidence

    clause_repo = ClauseRepository(session)
    for clause_extraction in envelope.clauses:
        # Construction-time guard (BR-CON-004, `Clause.__init__`) re-validates
        # page/text_span even though `ClauseExtraction` already required them -- defense
        # in depth, not redundant trust in the AI Gateway's own schema validation.
        clause = Clause(
            contract_version_id=version.id,
            clause_type=clause_extraction.clause_type,
            page=clause_extraction.page,
            text_span={
                "start": clause_extraction.text_span.start,
                "end": clause_extraction.text_span.end,
            },
            confidence=clause_extraction.confidence,
            text_excerpt=clause_extraction.text_excerpt,
        )
        clause_repo.add(clause)

    if confidence >= settings.contract_extraction_confidence_threshold and fields_dict:
        version.status = ContractVersionStatus.ANALYZED.value
    else:
        version.status = ContractVersionStatus.NEEDS_CONFIRMATION.value

    await emit_audit_event(
        session,
        event_type="contract.analysis_completed"
        if version.status == ContractVersionStatus.ANALYZED.value
        else "contract.analysis_needs_confirmation",
        actor_id=None,
        organization_id=document.organization_id,
        payload={
            "contract_id": str(version.contract_id),
            "contract_version_id": str(version.id),
            "extraction_confidence": confidence,
            "clause_count": len(envelope.clauses),
        },
    )

    await session.commit()
    await session.refresh(version)
    return version
