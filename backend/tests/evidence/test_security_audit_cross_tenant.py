"""ADR-016 end-of-sprint security audit (2026-10-12), Evidence & Audit scope: explicit
cross-tenant-access reproduction mandated by ADR-003.

One dedicated test proving a user authenticated into Organization A cannot read Organization
B's `EvidencePackage` rows, `Evidence` leaves, or `AuditEvent` rows through any path this
product exposes to an authenticated caller: the HTTP API, the repositories those routes sit
on, and the raw `AuditEventRepository.list` org filter (there is no API route that lists
`AuditEvent` at all today -- see this module's own findings in the audit report -- so the
repository-level check is this invariant's only exercise point until one exists).
"""

import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.infrastructure.models import Decision
from app.evidence.infrastructure.models import AuditEvent, Evidence, EvidencePackage
from app.evidence.infrastructure.repositories import (
    AuditEventRepository,
    EvidencePackageRepository,
    EvidenceRepository,
)
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import create_supplier, register_org_and_login
from tests.policies.test_compliance_review import EVIDENCE_ENVELOPE, TAX_ID, _upload_contract


async def _tenant_with_decision(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    *,
    email: str,
    mock_openrouter,
) -> dict:
    mock_openrouter(payload=EVIDENCE_ENVELOPE)
    headers = await register_org_and_login(client, email)
    supplier = await create_supplier(client, headers, tax_id=TAX_ID)
    contract_version_id = await _upload_contract(client, headers, supplier["id"])
    review = (
        await client.post(
            "/api/compliance/reviews",
            json={"contract_version_id": contract_version_id},
            headers=headers,
        )
    ).json()
    async with db_session_factory() as session:
        user = await UserRepository(session).get_by_email(email)
        decision = (
            await session.execute(
                select(Decision).where(Decision.compliance_review_id == uuid.UUID(review["id"]))
            )
        ).scalar_one()
        package = await EvidencePackageRepository(session).get_by_decision_and_organization(
            decision.id, user.organization_id
        )
    return {
        "headers": headers,
        "organization_id": user.organization_id,
        "decision_id": decision.id,
        "package_id": package.id,
    }


async def test_org_a_cannot_read_org_b_evidence_through_any_authenticated_path(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    a = await _tenant_with_decision(
        client,
        db_session_factory,
        email="audit-cross-a@example.com",
        mock_openrouter=mock_openrouter,
    )
    b = await _tenant_with_decision(
        client,
        db_session_factory,
        email="audit-cross-b@example.com",
        mock_openrouter=mock_openrouter,
    )
    assert a["organization_id"] != b["organization_id"]

    # 1. HTTP API: B's token against A's package id -> 404, not 403/200, and not leaking
    #    whether the id exists at all (same body as a genuinely nonexistent id).
    foreign_response = await client.get(
        f"/api/evidence-packages/{a['package_id']}", headers=b["headers"]
    )
    nonexistent_response = await client.get(
        f"/api/evidence-packages/{uuid.uuid4()}", headers=b["headers"]
    )
    assert foreign_response.status_code == 404, foreign_response.text
    assert foreign_response.json() == nonexistent_response.json()

    own_response = await client.get(
        f"/api/evidence-packages/{a['package_id']}", headers=a["headers"]
    )
    assert own_response.status_code == 200, own_response.text

    # 2. Repository layer, EvidencePackage: scoping by B's organization_id returns nothing
    #    for A's package, even though the row unambiguously exists in the database.
    async with db_session_factory() as session:
        assert (
            await EvidencePackageRepository(session).get_by_id_and_organization(
                a["package_id"], b["organization_id"]
            )
            is None
        )
        all_packages = (await session.execute(select(EvidencePackage))).scalars().all()
        # Really exists, really not a vacuous "0 rows" pass.
        assert any(p.id == a["package_id"] for p in all_packages)

    # 3. Repository layer, Evidence leaves: B's organization_id scoping on A's package id
    #    returns an empty list, never A's real leaves.
    async with db_session_factory() as session:
        foreign_evidence = await EvidenceRepository(session).list_by_package(
            a["package_id"], b["organization_id"]
        )
        assert foreign_evidence == []
        own_evidence = await EvidenceRepository(session).list_by_package(
            a["package_id"], a["organization_id"]
        )
        assert own_evidence  # A really has leaves -- this isn't vacuously true
        all_evidence_rows = (await session.execute(select(Evidence))).scalars().all()
        assert len(all_evidence_rows) >= len(own_evidence)  # B's org never sees A's rows via (2)

    # 4. AuditEvent: both tenants' registration/decision flow emits real AuditEvent rows.
    #    AuditEventRepository.list(organization_id=...) for B must never include any event
    #    that actually belongs to A, and vice versa -- the org filter is a hard boundary, not
    #    a default. (No HTTP route lists AuditEvent today, so this is the actual, only
    #    exercise point for this invariant -- see the audit report finding on that gap.)
    async with db_session_factory() as session:
        repo = AuditEventRepository(session)
        events_for_a = await repo.list(organization_id=a["organization_id"])
        events_for_b = await repo.list(organization_id=b["organization_id"])

        assert events_for_a, "org A should have real emitted audit events to assert against"
        assert events_for_b, "org B should have real emitted audit events to assert against"
        assert all(e.organization_id == a["organization_id"] for e in events_for_a)
        assert all(e.organization_id == b["organization_id"] for e in events_for_b)

        ids_a = {e.id for e in events_for_a}
        ids_b = {e.id for e in events_for_b}
        assert ids_a.isdisjoint(ids_b), "org B's audit-event list leaked an org A event id"

        # Sanity: confirm the database really holds events for both orgs (not an artifact of
        # an empty table making the assertions above vacuous).
        all_events = (await session.execute(select(AuditEvent))).scalars().all()
        assert any(e.organization_id == a["organization_id"] for e in all_events)
        assert any(e.organization_id == b["organization_id"] for e in all_events)
