"""FEATURE-8.1/8.2: anchors an `EvidencePackage`'s hash via the configured `AnchoringProvider`
(ADR-007) and lets a caller check back on its status. `evidence.anchored` is emitted once, when
a submission first reaches a terminal state (`confirmed` or `failed`) -- never on every
`check_anchor_status` poll, so re-checking an already-settled anchor is not itself an audited
action.

## Scope call (2026-10-07, matching this epic's own working method)
Auto-triggering anchoring the moment a Decision's `EvidencePackage` is assembled -- so every new
Decision gets an anchor with no human action -- needs wiring at every one of `create_decision_for_
review`'s several call sites (the synchronous APPROVE/BLOCK path, both `approval_service.approve_
request`/`reject_request` once a REVIEW chain resolves, and the re-evaluation sweep), each of which
owns its own commit boundary. Getting that fan-out right deserves its own pass rather than being
rushed at the tail of this one; `submit_anchor` below is a real, complete, independently callable
and tested entry point (`POST /evidence-packages/{id}/anchor`) in the meantime -- the same
"on-demand, not yet automatic" shape `evidence_package_service.recompute` already has for its own
read-only check. The auto-trigger wiring is tracked separately.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.evidence.application.audit_service import emit_audit_event
from app.evidence.application.evidence_package_service import get_package
from app.evidence.domain.anchoring import AnchoringProvider, AnchorStatus
from app.evidence.domain.errors import (
    AnchorAlreadySubmittedError,
    AnchoringProviderError,
    BlockchainAnchorNotFoundError,
)
from app.evidence.infrastructure.anchoring.constellation_provider import (
    ConstellationAnchoringProvider,
)
from app.evidence.infrastructure.anchoring.transparency_log_provider import (
    TransparencyLogAnchoringProvider,
)
from app.evidence.infrastructure.models import BlockchainAnchor
from app.evidence.infrastructure.repositories import BlockchainAnchorRepository

logger = logging.getLogger("jurisense.evidence.anchoring")


def get_provider() -> AnchoringProvider:
    """The one place a concrete `AnchoringProvider` is chosen, from `Settings.
    anchoring_provider` -- never sniffed from which credentials happen to be set (see that
    setting's own docstring)."""
    settings = get_settings()
    if settings.anchoring_provider == "constellation":
        missing = [
            name
            for name, value in (
                ("constellation_ded_api_key", settings.constellation_ded_api_key),
                ("constellation_ded_org_id", settings.constellation_ded_org_id),
                ("constellation_ded_tenant_id", settings.constellation_ded_tenant_id),
                ("constellation_ded_private_key", settings.constellation_ded_private_key),
            )
            if not value
        ]
        if missing:
            raise AnchoringProviderError(
                f"anchoring_provider is 'constellation' but missing settings: {', '.join(missing)}"
            )
        return ConstellationAnchoringProvider(
            base_url=settings.constellation_ded_base_url,
            api_key=settings.constellation_ded_api_key,
            org_id=settings.constellation_ded_org_id,
            tenant_id=settings.constellation_ded_tenant_id,
            private_key=settings.constellation_ded_private_key,
            timeout_seconds=settings.constellation_ded_timeout_seconds,
        )
    return TransparencyLogAnchoringProvider(
        repo_path=settings.transparency_log_repo_path,
        signing_key_path=settings.transparency_log_signing_key_path,
    )


@dataclass(frozen=True)
class AnchorResult:
    anchor: BlockchainAnchor
    newly_confirmed: bool


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.isoformat()


async def submit_anchor(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    evidence_package_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    provider: AnchoringProvider | None = None,
) -> AnchorResult:
    """Submits one EvidencePackage's `merkle_root` for anchoring. Raises
    `EvidencePackageNotFoundError` (via `get_package`) for a missing/foreign package, and
    `AnchorAlreadySubmittedError` if this package already has one (one anchor per package).
    An entry-point use case: commits on success. If the provider itself already confirms
    synchronously (the transparency log), `evidence.anchored` is emitted here; otherwise a
    later `check_anchor_status` call emits it once confirmation lands.

    QA review (2026-10-07): the up-front existence check below is only the common-case fast
    path, not the race guard -- `uq_blockchain_anchors_one_per_package` is. Two concurrent
    calls for the same package can both pass that check before either inserts; the row is
    claimed with a placeholder `anchor_ref` and flushed BEFORE calling `provider.submit_hash`
    specifically so the loser of that race hits the unique constraint (-> a clean
    `AnchorAlreadySubmittedError`) before ever reaching the provider -- for Constellation,
    submission is a real, presumably billable external call, so the loser must not make one.
    Mirrors `decision_service.create_decision_for_review`'s identical
    try/except-IntegrityError-then-rollback shape for its own unique constraints."""
    repository = BlockchainAnchorRepository(session)
    if await repository.get_by_package_and_organization(evidence_package_id, organization_id):
        raise AnchorAlreadySubmittedError()

    package_view = await get_package(
        session, organization_id=organization_id, package_id=evidence_package_id
    )
    active_provider = provider or get_provider()

    anchor = BlockchainAnchor(
        organization_id=organization_id,
        evidence_package_id=evidence_package_id,
        provider=active_provider.provider_name,
        anchor_ref=f"pending:{uuid.uuid4()}",  # replaced below, before any commit
        status=AnchorStatus.SUBMITTED.value,
    )
    repository.add(anchor)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        if _is_one_per_package_violation(exc):
            raise AnchorAlreadySubmittedError() from exc
        raise

    anchor.anchor_ref = await active_provider.submit_hash(package_view.package.merkle_root)
    await session.flush()

    newly_confirmed = await _refresh_from_provider(session, anchor=anchor, provider=active_provider)
    await session.commit()
    return AnchorResult(anchor=anchor, newly_confirmed=newly_confirmed)


def _is_one_per_package_violation(exc: IntegrityError) -> bool:
    """True only when the driver error reports a uniqueness violation on
    `uq_blockchain_anchors_one_per_package` -- mirrors `decision_service.
    _is_known_uniqueness_violation`'s exact matching approach (constraint name for
    PostgreSQL, the column SQLite's message names for the test database)."""
    text = f"{exc.orig} {getattr(exc.orig, '__cause__', '') or ''}".lower()
    if "unique" not in text:
        return False
    return (
        "uq_blockchain_anchors_one_per_package" in text
        or "blockchain_anchors.evidence_package_id" in text
    )


async def check_anchor_status(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    anchor_id: uuid.UUID,
    provider: AnchoringProvider | None = None,
) -> AnchorResult:
    """Re-checks a `submitted` anchor's current state against its provider. A no-op (no
    provider call, no write) once the anchor is already `confirmed`/`failed` -- settlement is
    terminal, matching `AnchorStatus`'s own docstring. Entry-point use case: commits."""
    repository = BlockchainAnchorRepository(session)
    anchor = await repository.get_by_id_and_organization(anchor_id, organization_id)
    if anchor is None:
        raise BlockchainAnchorNotFoundError()
    if anchor.status != AnchorStatus.SUBMITTED.value:
        return AnchorResult(anchor=anchor, newly_confirmed=False)

    active_provider = provider or get_provider()
    newly_confirmed = await _refresh_from_provider(session, anchor=anchor, provider=active_provider)
    await session.commit()
    return AnchorResult(anchor=anchor, newly_confirmed=newly_confirmed)


async def _refresh_from_provider(
    session: AsyncSession, *, anchor: BlockchainAnchor, provider: AnchoringProvider
) -> bool:
    """Mutates `anchor` in place from a fresh `get_proof` call. Returns whether this call is
    the one that first confirmed it (so the caller emits `evidence.anchored` exactly once,
    not on every poll and not for a failed settlement)."""
    proof = await provider.get_proof(anchor.anchor_ref)
    anchor.proof = dict(proof.raw)
    was_settled = anchor.status != AnchorStatus.SUBMITTED.value

    if proof.status is AnchorStatus.CONFIRMED:
        anchor.status = AnchorStatus.CONFIRMED.value
        anchor.confirmed_at = datetime.now(UTC)
    elif proof.status is AnchorStatus.FAILED:
        anchor.status = AnchorStatus.FAILED.value

    # `evidence.anchored` names a successful anchor (docs/03-domain/audit.md) -- a failed
    # settlement is not that event. It is still fully visible on the BlockchainAnchor row's
    # own `status`; this pass does not add a second, failure-specific audited event.
    newly_confirmed = not was_settled and anchor.status == AnchorStatus.CONFIRMED.value
    if newly_confirmed:
        await emit_audit_event(
            session,
            event_type="evidence.anchored",
            actor_id=None,
            organization_id=anchor.organization_id,
            payload={
                "blockchain_anchor_id": str(anchor.id),
                "evidence_package_id": str(anchor.evidence_package_id),
                "provider": anchor.provider,
                "anchor_ref": anchor.anchor_ref,
                "submitted_at": _iso(anchor.submitted_at),
                "confirmed_at": _iso(anchor.confirmed_at),
            },
        )
    return newly_confirmed


async def get_anchor(
    session: AsyncSession, *, organization_id: uuid.UUID, anchor_id: uuid.UUID
) -> BlockchainAnchor:
    anchor = await BlockchainAnchorRepository(session).get_by_id_and_organization(
        anchor_id, organization_id
    )
    if anchor is None:
        raise BlockchainAnchorNotFoundError()
    return anchor


async def get_anchor_for_package(
    session: AsyncSession, *, organization_id: uuid.UUID, evidence_package_id: uuid.UUID
) -> BlockchainAnchor | None:
    """`None` (never raises) when the package has no anchor yet -- a legitimate "not
    submitted" state the Decision Passport renders distinctly from "submitted"/"confirmed"."""
    return await BlockchainAnchorRepository(session).get_by_package_and_organization(
        evidence_package_id, organization_id
    )
