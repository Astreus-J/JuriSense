"""Security audit (2026-10-12): `compliance_reviews`, `rule_evaluations`, and
`policy_exceptions` were append-only only by repository convention (no update/delete
method exposed) -- the same gap #184 closed for the Evidence & Audit tables, now closed
here too (`app/core/append_only.py`, registered from `app/policies/infrastructure/
models.py`). These tests attempt the exact UPDATE/DELETE the trigger exists to stop,
directly against the session, bypassing every repository.

Uses `sqlalchemy.update()`/`delete()` Core constructs rather than raw `text()` SQL with a
hand-formatted id string: SQLite stores this codebase's UUID columns as 32-char hex with
no dashes, so a raw `WHERE id = :id` bound to `str(uuid_value)` (which has dashes) matches
zero rows and silently no-ops -- the Core constructs bind the real `Uuid` column type and
adapt correctly regardless of the underlying stored representation.

`decisions` is deliberately NOT covered (several genuine in-place mutation paths already
exist for it -- lifecycle transitions, the explicitly-modeled manual override,
re-evaluation tracking); no test for it is expected here.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.identity.infrastructure.repositories import UserRepository
from app.policies.infrastructure.models import ComplianceReview, PolicyException, RuleEvaluation
from tests.suppliers.conftest import register_org_and_login


async def _organization_id(db_session_factory: async_sessionmaker, email: str) -> uuid.UUID:
    async with db_session_factory() as session:
        return (await UserRepository(session).get_by_email(email)).organization_id


async def test_compliance_review_update_is_rejected_at_the_db_layer(
    client, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "append-only-review@example.com")
    org_id = await _organization_id(db_session_factory, "append-only-review@example.com")

    async with db_session_factory() as session:
        review = ComplianceReview(
            organization_id=org_id,
            contract_version_id=uuid.uuid4(),
            policy_version_ids=[],
            status="APPROVE",
            completed_at=datetime.now(UTC),
        )
        session.add(review)
        await session.commit()
        review_id = review.id

    async with db_session_factory() as session:
        with pytest.raises(IntegrityError, match="append-only"):
            await session.execute(
                update(ComplianceReview)
                .where(ComplianceReview.id == review_id)
                .values(status="BLOCK")
            )


async def test_compliance_review_delete_is_rejected_at_the_db_layer(
    client, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "append-only-review-delete@example.com")
    org_id = await _organization_id(db_session_factory, "append-only-review-delete@example.com")

    async with db_session_factory() as session:
        review = ComplianceReview(
            organization_id=org_id,
            contract_version_id=uuid.uuid4(),
            policy_version_ids=[],
            status="APPROVE",
            completed_at=datetime.now(UTC),
        )
        session.add(review)
        await session.commit()
        review_id = review.id

    async with db_session_factory() as session:
        with pytest.raises(IntegrityError, match="append-only"):
            await session.execute(delete(ComplianceReview).where(ComplianceReview.id == review_id))


async def test_rule_evaluation_update_is_rejected_at_the_db_layer(
    client, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "append-only-rule-eval@example.com")
    org_id = await _organization_id(db_session_factory, "append-only-rule-eval@example.com")

    async with db_session_factory() as session:
        review = ComplianceReview(
            organization_id=org_id,
            contract_version_id=uuid.uuid4(),
            policy_version_ids=[],
            status="BLOCK",
            completed_at=datetime.now(UTC),
        )
        session.add(review)
        await session.flush()
        evaluation = RuleEvaluation(
            compliance_review_id=review.id,
            rule_id=uuid.uuid4(),
            rule_key="SANC-001",
            rule_name="Test rule",
            outcome="BLOCK",
            severity="critical",
            rationale="test",
            evidence_refs=[],
        )
        session.add(evaluation)
        await session.commit()
        evaluation_id = evaluation.id

    async with db_session_factory() as session:
        with pytest.raises(IntegrityError, match="append-only"):
            await session.execute(
                update(RuleEvaluation)
                .where(RuleEvaluation.id == evaluation_id)
                .values(outcome="PASS")
            )


async def test_policy_exception_update_is_rejected_at_the_db_layer(
    client, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "append-only-exception@example.com")
    org_id = await _organization_id(db_session_factory, "append-only-exception@example.com")

    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("append-only-exception@example.com")
        exception = PolicyException(
            organization_id=org_id,
            rule_id=uuid.uuid4(),
            contract_version_id=uuid.uuid4(),
            justification="test",
            approver_role="legal",
            granted_by=admin.id,
            valid_until=datetime.now(UTC) + timedelta(days=1),
        )
        session.add(exception)
        await session.commit()
        exception_id = exception.id

    async with db_session_factory() as session:
        with pytest.raises(IntegrityError, match="append-only"):
            await session.execute(
                update(PolicyException)
                .where(PolicyException.id == exception_id)
                .values(justification="edited")
            )
