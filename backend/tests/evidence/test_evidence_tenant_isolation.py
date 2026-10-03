"""ADR-003: every new repository method and both GET routes (plus the recompute POST) deny
cross-tenant access, with 404 -- never 403, never an empty 200 -- and a foreign id is
indistinguishable from a nonexistent one."""

import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.approvals.infrastructure.models import Decision
from app.evidence.application import evidence_package_service
from app.evidence.domain.errors import EvidencePackageNotFoundError
from app.evidence.infrastructure.models import EvidencePackage
from app.evidence.infrastructure.repositories import EvidencePackageRepository, EvidenceRepository
from app.identity.infrastructure.repositories import UserRepository
from tests.approvals.conftest import create_supplier, register_org_and_login
from tests.evidence.conftest import create_user_and_login  # noqa: F401
from tests.policies.test_compliance_review import (
    EVIDENCE_ENVELOPE,
    TAX_ID,
    _upload_contract,
)


async def _tenant_with_package(
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


async def _two_tenants(client, db_session_factory, mock_openrouter, run_contract_extraction_inline):
    a = await _tenant_with_package(
        client, db_session_factory, email="iso-a@example.com", mock_openrouter=mock_openrouter
    )
    b = await _tenant_with_package(
        client, db_session_factory, email="iso-b@example.com", mock_openrouter=mock_openrouter
    )
    return a, b


async def test_get_package_by_id_is_404_for_another_tenant(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    a, b = await _two_tenants(
        client, db_session_factory, mock_openrouter, run_contract_extraction_inline
    )
    foreign = await client.get(f"/api/evidence-packages/{a['package_id']}", headers=b["headers"])
    missing = await client.get(f"/api/evidence-packages/{uuid.uuid4()}", headers=b["headers"])
    assert foreign.status_code == 404, foreign.text
    assert missing.status_code == 404, missing.text
    assert foreign.json() == missing.json()  # indistinguishable by design

    own = await client.get(f"/api/evidence-packages/{a['package_id']}", headers=a["headers"])
    assert own.status_code == 200, own.text


async def test_decision_passport_is_404_for_another_tenant(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    a, b = await _two_tenants(
        client, db_session_factory, mock_openrouter, run_contract_extraction_inline
    )
    foreign = await client.get(
        f"/api/decisions/{a['decision_id']}/evidence-package", headers=b["headers"]
    )
    missing = await client.get(
        f"/api/decisions/{uuid.uuid4()}/evidence-package", headers=b["headers"]
    )
    assert foreign.status_code == 404, foreign.text
    assert foreign.json() == missing.json()


async def test_recompute_is_404_for_another_tenant_and_writes_nothing(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    a, b = await _two_tenants(
        client, db_session_factory, mock_openrouter, run_contract_extraction_inline
    )
    response = await client.post(
        f"/api/evidence-packages/{a['package_id']}/recompute", headers=b["headers"]
    )
    assert response.status_code == 404, response.text

    own = await client.post(
        f"/api/evidence-packages/{a['package_id']}/recompute", headers=a["headers"]
    )
    assert own.status_code == 200, own.text
    assert own.json()["matches"] is True


async def test_role_without_evidence_read_is_refused(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    """RBAC (ADR-012): PROCUREMENT's grid has Evidence = none, so it gets 403 on the read route
    for its own organization's package -- the permission gate runs before any lookup."""
    a = await _tenant_with_package(
        client, db_session_factory, email="iso-rbac@example.com", mock_openrouter=mock_openrouter
    )
    procurement = await create_user_and_login(
        client, a["headers"], email="procurement-iso@example.com", role="procurement"
    )
    response = await client.get(f"/api/evidence-packages/{a['package_id']}", headers=procurement)
    assert response.status_code == 403, response.text


async def test_package_repository_methods_deny_another_tenant(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    a, b = await _two_tenants(
        client, db_session_factory, mock_openrouter, run_contract_extraction_inline
    )
    async with db_session_factory() as session:
        repository = EvidencePackageRepository(session)
        assert (
            await repository.get_by_id_and_organization(a["package_id"], b["organization_id"])
            is None
        )
        assert (
            await repository.get_by_decision_and_organization(
                a["decision_id"], b["organization_id"]
            )
            is None
        )
        assert (
            await repository.get_by_id_and_organization(a["package_id"], a["organization_id"])
            is not None
        )


async def test_evidence_repository_lists_nothing_for_another_tenant(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    a, b = await _two_tenants(
        client, db_session_factory, mock_openrouter, run_contract_extraction_inline
    )
    async with db_session_factory() as session:
        assert (
            await EvidenceRepository(session).list_by_package(a["package_id"], b["organization_id"])
            == []
        )
        own = await EvidenceRepository(session).list_by_package(
            a["package_id"], a["organization_id"]
        )
        assert own


async def test_service_functions_raise_not_found_for_another_tenant(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    mock_openrouter,
    run_contract_extraction_inline,
) -> None:
    a, b = await _two_tenants(
        client, db_session_factory, mock_openrouter, run_contract_extraction_inline
    )
    async with db_session_factory() as session:
        for call in (
            evidence_package_service.get_package(
                session, organization_id=b["organization_id"], package_id=a["package_id"]
            ),
            evidence_package_service.get_package_for_decision(
                session, organization_id=b["organization_id"], decision_id=a["decision_id"]
            ),
            evidence_package_service.recompute(
                session, organization_id=b["organization_id"], package_id=a["package_id"]
            ),
        ):
            try:
                await call
            except EvidencePackageNotFoundError:
                continue
            raise AssertionError("cross-tenant call must raise EvidencePackageNotFoundError")

    async with db_session_factory() as session:
        packages = (await session.execute(select(EvidencePackage))).scalars().all()
        assert len(packages) == 2
