"""Contract/ContractVersion creation (CON-001, CON-002, BR-CON-001, BR-CON-002).

`upload_contract_version` is the single entrypoint for both "upload the first version of
a brand-new contract" and "upload a new negotiation round against an existing contract" --
the two Plane stories (#42 upload, #45 versioning) are one pipeline in practice, exactly
as `docs/03-domain/contract-compliance.md`'s pipeline describes them as consecutive steps
of the same flow.
"""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.application import document_service, extraction_orchestration
from app.contracts.domain.constants import ContractStatus, ContractVersionStatus
from app.contracts.domain.errors import (
    ConcurrentVersionConflictError,
    ContractNotFoundError,
    ContractVersionNotFoundError,
    InvalidSupplierReferenceError,
    MissingContractMetadataError,
    SupplierMismatchError,
)
from app.contracts.infrastructure.models import Contract, ContractVersion
from app.contracts.infrastructure.repositories import ContractRepository, ContractVersionRepository
from app.core.storage import StoragePort
from app.evidence.application.audit_service import emit_audit_event
from app.suppliers.application.supplier_service import supplier_belongs_to_organization


async def upload_contract_version(
    session: AsyncSession,
    *,
    storage: StoragePort,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    supplier_id: uuid.UUID,
    filename: str,
    data: bytes,
    contract_id: uuid.UUID | None = None,
    title: str | None = None,
    contract_type: str | None = None,
) -> ContractVersion:
    # Security review (2026-09-29): checked before anything is created/uploaded --
    # previously a new Contract trusted `supplier_id` outright and only the DB's FK
    # constraint caught a *nonexistent* one, letting a real supplier belonging to a
    # *different* organization through (confirmed live). Checked up front, ahead of the
    # storage write below, so a rejected request never wastes a document upload either.
    if not await supplier_belongs_to_organization(
        session, organization_id=organization_id, supplier_id=supplier_id
    ):
        raise InvalidSupplierReferenceError()

    document = await document_service.upload_document(
        session,
        storage=storage,
        organization_id=organization_id,
        actor_id=actor_id,
        filename=filename,
        data=data,
    )

    contract_repo = ContractRepository(session)
    is_new_contract = contract_id is None

    if contract_id is not None:
        contract = await contract_repo.get_by_id_and_organization(contract_id, organization_id)
        if contract is None:
            raise ContractNotFoundError()
        # BR-CON-001: a Contract belongs to exactly one Supplier -- re-upload against an
        # existing contract may not silently reassign it to a different supplier.
        if contract.supplier_id != supplier_id:
            raise SupplierMismatchError(
                f"Contract {contract_id} belongs to a different supplier than the one given"
            )
    else:
        if not title or not contract_type:
            raise MissingContractMetadataError(
                "title and contract_type are required when creating a new contract "
                "(no contract_id given)"
            )
        contract = Contract(
            organization_id=organization_id,
            supplier_id=supplier_id,
            title=title,
            contract_type=contract_type,
            status=ContractStatus.DRAFT.value,
        )
        contract_repo.add(contract)
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            raise InvalidSupplierReferenceError() from exc

    version_repo = ContractVersionRepository(session)
    version_number = await version_repo.get_next_version_number(contract.id)
    version = ContractVersion(
        contract_id=contract.id,
        document_id=document.id,
        version_number=version_number,
        status=ContractVersionStatus.EXTRACTED.value,
        extracted_data={},
        extraction_confidence=None,
    )
    version_repo.add(version)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        # QA review (2026-09-29): the just-uploaded Document (and its two audit events)
        # is now orphaned -- no ContractVersion ever references it. Not cleaned up here:
        # Document is documented as immutable/never-deleted (domain-model.md's
        # `uploaded -> processed -> (archived)` lifecycle has no delete state), so an
        # unreferenced-but-retained row is the accepted trade-off for a rare race,
        # consistent with this codebase's append-only philosophy elsewhere.
        raise ConcurrentVersionConflictError() from exc
    await session.refresh(version)

    await emit_audit_event(
        session,
        event_type="contract.created" if is_new_contract else "contract.version_created",
        actor_id=actor_id,
        organization_id=organization_id,
        payload={
            "contract_id": str(contract.id),
            "contract_version_id": str(version.id),
            "version_number": version.version_number,
            "document_id": str(document.id),
        },
    )

    # CON-003: AI extraction is dispatched for every new ContractVersion, committed
    # before enqueueing (`trigger_extraction`'s own docstring) so the worker's own
    # session already sees this row.
    await extraction_orchestration.trigger_extraction(session, contract_version=version)

    return version


async def list_contracts(session: AsyncSession, *, organization_id: uuid.UUID) -> list[Contract]:
    return await ContractRepository(session).list_by_organization(organization_id)


async def get_contract(
    session: AsyncSession, *, organization_id: uuid.UUID, contract_id: uuid.UUID
) -> Contract:
    contract = await ContractRepository(session).get_by_id_and_organization(
        contract_id, organization_id
    )
    if contract is None:
        raise ContractNotFoundError()
    return contract


async def list_contract_versions(
    session: AsyncSession, *, organization_id: uuid.UUID, contract_id: uuid.UUID
) -> list[ContractVersion]:
    await get_contract(session, organization_id=organization_id, contract_id=contract_id)
    return await ContractVersionRepository(session).list_by_contract(contract_id)


async def get_contract_version(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    contract_id: uuid.UUID,
    version_id: uuid.UUID,
) -> ContractVersion:
    await get_contract(session, organization_id=organization_id, contract_id=contract_id)
    version = await ContractVersionRepository(session).get_by_id(version_id)
    if version is None or version.contract_id != contract_id:
        raise ContractVersionNotFoundError()
    return version
