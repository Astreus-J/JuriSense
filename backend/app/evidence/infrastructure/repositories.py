import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.infrastructure.models import (
    AuditEvent,
    BlockchainAnchor,
    Evidence,
    EvidenceOverrideAddendum,
    EvidencePackage,
)


class AuditEventRepository:
    """Append-only repository for AuditEvent.

    Intentionally exposes only `add`/`get`/`list` -- no `update` or `delete` method exists
    anywhere on this class. This is the enforcement mechanism for BR-EVD-003/AUD-002: no
    actor, including Admin/Auditor roles, has any path to modify or remove a recorded
    event (see tests/evidence/test_audit_event.py's negative test).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event: AuditEvent) -> None:
        self._session.add(event)

    async def get(self, event_id: uuid.UUID) -> AuditEvent | None:
        """Fetch a single event by id, unscoped by organization.

        No route calls this yet. Whoever adds the first one (EPIC-7, Evidence & Audit)
        MUST add its own organization_id check on the result before returning it to a
        caller -- `list()` already enforces tenant scoping, this method deliberately does
        not, since a single-event lookup's caller-side scoping needs depend on that
        route's own authorization shape.
        """
        return await self._session.get(AuditEvent, event_id)

    async def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        event_type: str | None = None,
    ) -> list[AuditEvent]:
        query = select(AuditEvent).order_by(AuditEvent.occurred_at)
        if organization_id is not None:
            query = query.where(AuditEvent.organization_id == organization_id)
        if event_type is not None:
            query = query.where(AuditEvent.event_type == event_type)
        result = await self._session.execute(query)
        return list(result.scalars())


class EvidencePackageRepository:
    """Append-only, tenant-scoped repository for EvidencePackage. Exposes `add` and
    organization-scoped reads only -- no update or delete (BR-EVD-003's spirit applied to
    the package, docs/03-domain/evidence.md)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, package: EvidencePackage) -> None:
        self._session.add(package)

    async def get_by_id_and_organization(
        self, package_id: uuid.UUID, organization_id: uuid.UUID
    ) -> EvidencePackage | None:
        result = await self._session.execute(
            select(EvidencePackage).where(
                EvidencePackage.id == package_id,
                EvidencePackage.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_decision_and_organization(
        self, decision_id: uuid.UUID, organization_id: uuid.UUID, *, for_update: bool = False
    ) -> EvidencePackage | None:
        """`for_update=True` (QA/security review, 2026-10-10, #187) takes a row lock on the
        package, held until the caller's transaction ends -- `record_override_addendum` uses
        this to serialize concurrent overrides of the same Decision, so two overrides can
        never read the same "latest addendum" and compute the same `sequence_number`. A no-op
        on SQLite (the test suite's backend), which doesn't support row locking; the
        `uq_evidence_override_addenda_one_per_sequence` constraint is the backstop there."""
        query = select(EvidencePackage).where(
            EvidencePackage.decision_id == decision_id,
            EvidencePackage.organization_id == organization_id,
        )
        if for_update:
            query = query.with_for_update()
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_decision_id_any_organization(
        self, decision_id: uuid.UUID
    ) -> EvidencePackage | None:
        """FEATURE-8.3 (STORY-8.3.1): the one deliberate exception to this repository's
        tenant scoping. Backs the PUBLIC, unauthenticated verification page
        (`docs/06-blockchain/verification.md`) -- a visitor with no organization context at
        all, by design (an external auditor, a counterparty, a hackathon judge), who already
        holds the specific `Decision` id they want to check. Every caller of this method
        MUST be that public verification path; nothing else in the product may read across
        organizations like this. The method name says so on purpose, so a reviewer scanning
        call sites never mistakes this for an oversight."""
        result = await self._session.execute(
            select(EvidencePackage).where(EvidencePackage.decision_id == decision_id)
        )
        return result.scalar_one_or_none()

    async def get_by_merkle_root_any_organization(self, merkle_root: str) -> EvidencePackage | None:
        """Same deliberate exception as `get_by_decision_id_any_organization`, for a visitor
        who pastes the raw hash instead of a Decision id. `merkle_root` has no uniqueness
        constraint at the database level (two different packages sharing one would require a
        SHA-256 collision) -- `.first()` rather than `scalar_one_or_none()` so that
        astronomically unlikely case degrades to "resolves one of them" instead of an
        unhandled exception on a public, unauthenticated path."""
        result = await self._session.execute(
            select(EvidencePackage).where(EvidencePackage.merkle_root == merkle_root)
        )
        return result.scalars().first()


class EvidenceRepository:
    """Append-only, tenant-scoped repository for the Evidence leaves of a package."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, evidence: Evidence) -> None:
        self._session.add(evidence)

    async def list_by_package(
        self, package_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[Evidence]:
        result = await self._session.execute(
            select(Evidence)
            .where(
                Evidence.evidence_package_id == package_id,
                Evidence.organization_id == organization_id,
            )
            .order_by(Evidence.type, Evidence.ref_id)
        )
        return list(result.scalars())


class EvidenceOverrideAddendumRepository:
    """Append-only, tenant-scoped repository for `EvidenceOverrideAddendum` (#187). Exposes
    `add` and reads only, same append-only spirit as `EvidencePackageRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, addendum: EvidenceOverrideAddendum) -> None:
        self._session.add(addendum)

    async def list_by_package(
        self, evidence_package_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[EvidenceOverrideAddendum]:
        result = await self._session.execute(
            select(EvidenceOverrideAddendum)
            .where(
                EvidenceOverrideAddendum.evidence_package_id == evidence_package_id,
                EvidenceOverrideAddendum.organization_id == organization_id,
            )
            .order_by(EvidenceOverrideAddendum.sequence_number)
        )
        return list(result.scalars())

    async def get_latest_for_package(
        self, evidence_package_id: uuid.UUID, organization_id: uuid.UUID
    ) -> EvidenceOverrideAddendum | None:
        result = await self._session.execute(
            select(EvidenceOverrideAddendum)
            .where(
                EvidenceOverrideAddendum.evidence_package_id == evidence_package_id,
                EvidenceOverrideAddendum.organization_id == organization_id,
            )
            .order_by(EvidenceOverrideAddendum.sequence_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class BlockchainAnchorRepository:
    """Tenant-scoped repository for BlockchainAnchor (FEATURE-8.2). Exposes `add` and
    organization-scoped reads only -- unlike `Evidence`/`EvidencePackage`, an anchor's
    `status`/`proof`/`confirmed_at` legitimately change in place as the underlying network
    settles (`anchoring_service._refresh_from_provider` does this directly on the ORM
    object it already holds, via the session's own change tracking, rather than through a
    dedicated update method here), so this repository is not append-only in spirit even
    though it has no update method of its own."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, anchor: BlockchainAnchor) -> None:
        self._session.add(anchor)

    async def get_by_id_and_organization(
        self, anchor_id: uuid.UUID, organization_id: uuid.UUID
    ) -> BlockchainAnchor | None:
        result = await self._session.execute(
            select(BlockchainAnchor).where(
                BlockchainAnchor.id == anchor_id,
                BlockchainAnchor.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_package_and_organization(
        self, evidence_package_id: uuid.UUID, organization_id: uuid.UUID
    ) -> BlockchainAnchor | None:
        result = await self._session.execute(
            select(BlockchainAnchor).where(
                BlockchainAnchor.evidence_package_id == evidence_package_id,
                BlockchainAnchor.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_package_id_any_organization(
        self, evidence_package_id: uuid.UUID
    ) -> BlockchainAnchor | None:
        """FEATURE-8.3: the same deliberate, named exception to tenant scoping as
        `EvidencePackageRepository.get_by_decision_id_any_organization` -- backs the public
        verification page only."""
        result = await self._session.execute(
            select(BlockchainAnchor).where(
                BlockchainAnchor.evidence_package_id == evidence_package_id
            )
        )
        return result.scalar_one_or_none()
