"""#184: audit_events, evidence_packages and evidence are append-only enforced by a DB trigger,
not just by the repositories' own missing update/delete methods. #187 added
evidence_override_addenda under the same guarantee. Exercises the trigger directly with raw SQL,
bypassing the ORM/repository layer entirely -- the exact bypass the trigger exists to stop."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.evidence.infrastructure.models import (
    AuditEvent,
    Evidence,
    EvidenceOverrideAddendum,
    EvidencePackage,
)


async def _insert_audit_event(engine: AsyncEngine) -> uuid.UUID:
    event_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            insert(AuditEvent).values(
                id=event_id,
                event_type="test.event",
                actor_id=None,
                organization_id=None,
                payload={},
            )
        )
    return event_id


async def test_audit_events_reject_update(db_engine: AsyncEngine) -> None:
    event_id = await _insert_audit_event(db_engine)
    with pytest.raises(DBAPIError):
        async with db_engine.begin() as conn:
            await conn.execute(
                update(AuditEvent).where(AuditEvent.id == event_id).values(event_type="tampered")
            )


async def test_audit_events_reject_delete(db_engine: AsyncEngine) -> None:
    event_id = await _insert_audit_event(db_engine)
    with pytest.raises(DBAPIError):
        async with db_engine.begin() as conn:
            await conn.execute(delete(AuditEvent).where(AuditEvent.id == event_id))


async def _insert_package(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    org_id = uuid.uuid4()
    package_id = uuid.uuid4()
    decision_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            insert(EvidencePackage).values(
                id=package_id,
                organization_id=org_id,
                decision_id=decision_id,
                merkle_root="a" * 64,
                evidence_count=0,
            )
        )
    return org_id, package_id


async def test_evidence_packages_reject_update(db_engine: AsyncEngine) -> None:
    _, package_id = await _insert_package(db_engine)
    with pytest.raises(DBAPIError):
        async with db_engine.begin() as conn:
            await conn.execute(
                update(EvidencePackage)
                .where(EvidencePackage.id == package_id)
                .values(merkle_root="b" * 64)
            )


async def test_evidence_packages_reject_delete(db_engine: AsyncEngine) -> None:
    _, package_id = await _insert_package(db_engine)
    with pytest.raises(DBAPIError):
        async with db_engine.begin() as conn:
            await conn.execute(delete(EvidencePackage).where(EvidencePackage.id == package_id))


async def test_evidence_rows_reject_update_and_delete(db_engine: AsyncEngine) -> None:
    org_id, package_id = await _insert_package(db_engine)
    evidence_id = uuid.uuid4()
    async with db_engine.begin() as conn:
        await conn.execute(
            insert(Evidence).values(
                id=evidence_id,
                organization_id=org_id,
                evidence_package_id=package_id,
                type="decision",
                ref_id="d1",
                payload={},
                content_hash="c" * 64,
            )
        )

    with pytest.raises(DBAPIError):
        async with db_engine.begin() as conn:
            await conn.execute(
                update(Evidence).where(Evidence.id == evidence_id).values(content_hash="d" * 64)
            )
    with pytest.raises(DBAPIError):
        async with db_engine.begin() as conn:
            await conn.execute(delete(Evidence).where(Evidence.id == evidence_id))

    async with db_engine.begin() as conn:
        result = await conn.execute(select(Evidence).where(Evidence.id == evidence_id))
        assert result.first() is not None  # the rejected delete above did not go through


async def test_evidence_override_addenda_reject_update_and_delete(db_engine: AsyncEngine) -> None:
    org_id, package_id = await _insert_package(db_engine)
    decision_id = uuid.uuid4()
    addendum_id = uuid.uuid4()
    async with db_engine.begin() as conn:
        await conn.execute(
            insert(EvidenceOverrideAddendum).values(
                id=addendum_id,
                organization_id=org_id,
                evidence_package_id=package_id,
                decision_id=decision_id,
                sequence_number=1,
                original_status="BLOCK",
                new_status="APPROVE",
                justification="test",
                overridden_by=uuid.uuid4(),
                overridden_at=datetime.now(UTC),
                previous_hash=None,
                content_hash="e" * 64,
            )
        )

    with pytest.raises(DBAPIError):
        async with db_engine.begin() as conn:
            await conn.execute(
                update(EvidenceOverrideAddendum)
                .where(EvidenceOverrideAddendum.id == addendum_id)
                .values(new_status="BLOCK")
            )
    with pytest.raises(DBAPIError):
        async with db_engine.begin() as conn:
            await conn.execute(
                delete(EvidenceOverrideAddendum).where(
                    EvidenceOverrideAddendum.id == addendum_id
                )
            )
