"""SupplierCheck orchestration (SUP-002, SUP-003, SUP-004, SUP-005).

`trigger_check` (called from `supplier_service.create_supplier` and the manual re-check
route) only ever creates the `started` `SupplierCheck` row and enqueues the worker — the
actual verification (`run_supplier_check`) always runs out-of-band, exactly like a real
Celery task would, so this module has one seam (`enqueue_supplier_check`) tests replace
to run the same async logic synchronously against the test database instead of a real
worker (see tests/conftest.py).
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.application.audit_service import emit_audit_event
from app.integrations.application.supplier_verification_service import (
    get_supplier_verification_port,
)
from app.integrations.domain.ports import VerificationOutcome
from app.suppliers.domain.constants import (
    AddressFlag,
    RegistryStatus,
    SupplierCheckStatus,
    SupplierStatus,
)
from app.suppliers.domain.errors import SupplierCheckNotFoundError, SupplierNotFoundError
from app.suppliers.infrastructure.models import Supplier, SupplierCheck, SupplierProfile
from app.suppliers.infrastructure.repositories import (
    SupplierCheckRepository,
    SupplierProfileRepository,
)

logger = logging.getLogger("jurisense.suppliers.checks")

# Sources every check queries today (supplier-compliance.md "Data sources"); the
# "Internal history" source is not yet wired (Phase-2 scope was the two external
# categories — see ADR-017).
_SOURCES_CONSULTED = ["cnpj_registry", "sanctions"]

_REGISTRY_STATUS_MAP = {
    "ATIVA": RegistryStatus.ACTIVE,
    "SUSPENSA": RegistryStatus.SUSPENDED,
    "INAPTA": RegistryStatus.SUSPENDED,
    "BAIXADA": RegistryStatus.CANCELLED,
    "NULA": RegistryStatus.CANCELLED,
}


async def trigger_check(session: AsyncSession, *, supplier: Supplier) -> SupplierCheck:
    """Creates the `started` SupplierCheck row and enqueues the worker (SUP-002). Used
    both for the initial check on supplier creation and for manual re-check."""
    check = SupplierCheck(
        supplier_id=supplier.id,
        status=SupplierCheckStatus.STARTED.value,
        sources_consulted=list(_SOURCES_CONSULTED),
    )
    SupplierCheckRepository(session).add(check)
    await session.commit()
    await session.refresh(check)

    await emit_audit_event(
        session,
        event_type="supplier.check.started",
        actor_id=None,
        organization_id=supplier.organization_id,
        payload={"supplier_id": str(supplier.id), "check_id": str(check.id)},
    )
    await session.commit()

    await enqueue_supplier_check(check.id)
    return check


async def enqueue_supplier_check(check_id: uuid.UUID) -> None:
    """Hands the check off to the Celery worker (fire-and-forget: `.delay()` itself is
    synchronous/non-blocking — `async def` only so this call composes with `await`).

    This is the one seam `tests/conftest.py` monkeypatches (module-qualified, i.e. tests
    patch `check_service.enqueue_supplier_check`, and callers must invoke it via
    `check_service.enqueue_supplier_check(...)` rather than a bound import, for the
    monkeypatch to take effect) to run `run_supplier_check` synchronously against the
    test database instead of requiring a real broker/worker — the same idea as
    `app.identity.api.deps.get_email_sender` being swapped for a capturing stub in tests.
    """
    from app.suppliers.infrastructure.tasks import run_supplier_check_task

    run_supplier_check_task.delay(str(check_id))


def _normalize_registry_status(data: dict[str, Any]) -> RegistryStatus:
    if data.get("not_found"):
        return RegistryStatus.UNKNOWN
    raw_status = (data.get("descricao_situacao_cadastral") or "").strip().upper()
    return _REGISTRY_STATUS_MAP.get(raw_status, RegistryStatus.UNKNOWN)


def _normalize_responsible_parties(data: dict[str, Any]) -> list[dict[str, Any]]:
    parties = []
    for partner in data.get("qsa") or []:
        parties.append(
            {
                "name": partner.get("nome_socio"),
                "role": partner.get("qualificacao_socio"),
                "document_masked": partner.get("cnpj_cpf_do_socio"),
            }
        )
    return parties


def _normalize_address(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "street": data.get("logradouro"),
        "number": data.get("numero"),
        "district": data.get("bairro"),
        "city": data.get("municipio"),
        "state": data.get("uf"),
        "postal_code": data.get("cep"),
    }


def _address_flag(registry_ok: bool, address: dict[str, Any]) -> AddressFlag:
    """Heuristic per supplier-compliance.md §4 — a REVIEW-tier signal, never BLOCK on its
    own. A fuller "declared activity vs. CNAE" comparison needs a declared-activity input
    this phase's minimal Supplier fields (legal_name/tax_id/jurisdiction) don't capture
    yet — documented simplification, not silently skipped (see ADR-017)."""
    if not registry_ok:
        return AddressFlag.UNKNOWN
    if not address.get("city") or not address.get("state"):
        return AddressFlag.FLAGGED
    return AddressFlag.CONSISTENT


def _build_profile_fields(
    outcome: VerificationOutcome, *, previous_profile: SupplierProfile | None
) -> dict[str, Any]:
    by_source = {result.source: result for result in outcome.results}
    registry = by_source["cnpj_registry"]
    sanctions = by_source["sanctions"]

    registry_ok = registry.status == "ok"
    address = _normalize_address(registry.data) if registry_ok else {}
    new_hits = list(sanctions.data.get("hits", [])) if sanctions.status == "ok" else []
    for hit in new_hits:
        hit["carried_forward"] = False

    # BR-SUP-004 / SUP-004: sticky-true. A routine re-check that finds no fresh hit must
    # never silently clear a previously recorded sanctions flag — only an explicit
    # override/exception record (EPIC-4 scope) may do that.
    previously_flagged = bool(previous_profile and previous_profile.sanctions_hit)
    sanctions_hit = bool(new_hits) or previously_flagged
    if new_hits:
        sanctions_detail = new_hits
    elif previously_flagged:
        sanctions_detail = previous_profile.sanctions_detail
    else:
        sanctions_detail = []

    return {
        "registry_status": _normalize_registry_status(registry.data if registry_ok else {}).value,
        "legal_name": registry.data.get("razao_social") if registry_ok else None,
        "corporate_structure": {
            "legal_nature": registry.data.get("natureza_juridica"),
            "incorporation_date": registry.data.get("data_inicio_atividade"),
            "capital_social": registry.data.get("capital_social"),
            "secondary_activities": registry.data.get("cnaes_secundarios"),
        }
        if registry_ok
        else {},
        "responsible_parties": _normalize_responsible_parties(registry.data) if registry_ok else [],
        "cnae_code": registry.data.get("cnae_fiscal") if registry_ok else None,
        "cnae_description": registry.data.get("cnae_fiscal_descricao") if registry_ok else None,
        "address": address,
        "activity_mismatch": False,  # documented simplification — see _address_flag docstring
        "address_flag": _address_flag(registry_ok, address).value,
        "sanctions_hit": sanctions_hit,
        "sanctions_detail": sanctions_detail,
    }


async def run_supplier_check(session: AsyncSession, *, check_id: uuid.UUID) -> SupplierCheck:
    """The actual verification logic (supplier-compliance.md steps 2-6). Runs inside the
    Celery task in production; tests call it directly through the monkeypatched
    `enqueue_supplier_check` seam."""
    check_repo = SupplierCheckRepository(session)
    check = await check_repo.get_by_id(check_id)
    if check is None:
        raise SupplierCheckNotFoundError()

    supplier = await session.get(Supplier, check.supplier_id)
    if supplier is None:
        raise SupplierNotFoundError()

    port = get_supplier_verification_port(session)
    outcome = await port.verify(
        tax_id=supplier.tax_id, jurisdiction=supplier.jurisdiction, legal_name=supplier.legal_name
    )
    raw_results = outcome.raw_results()

    if outcome.any_mandatory_source_unavailable():
        # supplier-compliance.md step 3: an incomplete mandatory source must never look
        # like a clean check — the whole check fails instead of completing.
        await check_repo.mark_failed(
            check,
            raw_results=raw_results,
            reason="One or more mandatory sources (cnpj_registry, sanctions) were unavailable",
        )
        await emit_audit_event(
            session,
            event_type="supplier.check.failed",
            actor_id=None,
            organization_id=supplier.organization_id,
            payload={
                "supplier_id": str(supplier.id),
                "check_id": str(check.id),
                "reason": check.failure_reason,
            },
        )
        await session.commit()
        logger.warning("SupplierCheck %s failed: mandatory source unavailable", check.id)
        return check

    await check_repo.mark_completed(check, raw_results=raw_results)

    profile_repo = SupplierProfileRepository(session)
    previous_profile = await profile_repo.get_current_by_supplier(supplier.id)
    fields = _build_profile_fields(outcome, previous_profile=previous_profile)

    new_profile = SupplierProfile(
        supplier_id=supplier.id,
        source_check_id=check.id,
        is_current=True,
        created_at=datetime.now(UTC),
        **fields,
    )
    await profile_repo.replace_current(new_profile)

    await emit_audit_event(
        session,
        event_type="supplier.check.completed",
        actor_id=None,
        organization_id=supplier.organization_id,
        payload={"supplier_id": str(supplier.id), "check_id": str(check.id)},
    )
    await emit_audit_event(
        session,
        event_type="supplier.profile_updated",
        actor_id=None,
        organization_id=supplier.organization_id,
        payload={
            "supplier_id": str(supplier.id),
            "sanctions_hit": new_profile.sanctions_hit,
            "registry_status": new_profile.registry_status,
        },
    )

    # Prospect -> under_review the moment the pipeline has actually started producing a
    # verification outcome; an already-decided supplier (approved/blocked/inactive)
    # keeps its status — a re-check result on it feeds Policy & Compliance's
    # `compliance.review_required` path (BR-DEC-004), not an automatic status flip here.
    if supplier.status == SupplierStatus.PROSPECT.value:
        supplier.status = SupplierStatus.UNDER_REVIEW.value

    await session.commit()
    await session.refresh(check)
    return check
