import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.contracts.api.schemas import (
    ClauseResponse,
    ConfirmContractVersionRequest,
    ContractResponse,
    ContractVersionResponse,
)
from app.contracts.application import confirmation_service, contract_service
from app.contracts.domain.errors import (
    ConcurrentVersionConflictError,
    ContractLimitExceededError,
    ContractNotFoundError,
    ContractVersionNotFoundError,
    ContractVersionNotReadyForConfirmationError,
    FileTooLargeError,
    InvalidSupplierReferenceError,
    MalwareDetectedError,
    MissingContractMetadataError,
    SupplierMismatchError,
    UnsupportedFileTypeError,
)
from app.contracts.domain.extracted_data import low_confidence_paths
from app.contracts.infrastructure.models import ContractVersion
from app.contracts.infrastructure.repositories import ClauseRepository
from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.storage import StorageDep
from app.identity.api.deps import rate_limit_by_organization, require_permission
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import User

router = APIRouter(prefix="/contracts", tags=["contracts"])


def _to_version_response(version: ContractVersion) -> ContractVersionResponse:
    """See ContractVersionResponse.needs_confirmation_paths' docstring -- computed here,
    once, so every route returns it consistently rather than each call site
    re-deriving (or forgetting to derive) it."""
    threshold = get_settings().contract_extraction_confidence_threshold
    paths = low_confidence_paths(version.extracted_data.get("fields", {}), threshold=threshold)
    response = ContractVersionResponse.model_validate(version)
    response.needs_confirmation_paths = paths
    return response

CanCreateContracts = Annotated[User, Depends(require_permission(Module.CONTRACTS, "create"))]
CanReadContracts = Annotated[User, Depends(require_permission(Module.CONTRACTS, "read"))]
CanUpdateContracts = Annotated[User, Depends(require_permission(Module.CONTRACTS, "update"))]

# #143: every upload dispatches AI extraction (CON-003) -- a real external API call (the
# configured AI Gateway provider) plus a Celery task, the same external-call shape the
# load test found unthrottled for Suppliers.
_settings = get_settings()
ContractUploadRateLimited = Annotated[
    None,
    Depends(
        rate_limit_by_organization(
            max_requests=_settings.external_call_rate_limit_max_requests,
            window_seconds=_settings.external_call_rate_limit_window_seconds,
            key_prefix="contract_upload",
        )
    ),
]

_UPLOAD_ERROR_MAP = {
    UnsupportedFileTypeError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    FileTooLargeError: status.HTTP_413_CONTENT_TOO_LARGE,
    MalwareDetectedError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    MissingContractMetadataError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    SupplierMismatchError: status.HTTP_409_CONFLICT,
    InvalidSupplierReferenceError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ContractNotFoundError: status.HTTP_404_NOT_FOUND,
    ConcurrentVersionConflictError: status.HTTP_409_CONFLICT,
    ContractLimitExceededError: status.HTTP_403_FORBIDDEN,
}


@router.post("/upload", response_model=ContractVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_contract_version(
    user: CanCreateContracts,
    session: SessionDep,
    storage: StorageDep,
    _: ContractUploadRateLimited,
    file: Annotated[UploadFile, File()],
    supplier_id: Annotated[uuid.UUID, Form()],
    contract_id: Annotated[uuid.UUID | None, Form()] = None,
    title: Annotated[str | None, Form()] = None,
    contract_type: Annotated[str | None, Form()] = None,
) -> ContractVersionResponse:
    """CON-001/CON-002: uploads a contract document (PDF/DOCX/TXT), scanned/validated
    synchronously (SEC-003) before anything is persisted. Omit `contract_id` to create a
    brand-new `Contract` (requires `title`/`contract_type`); pass an existing
    `contract_id` to add a new negotiation-round `ContractVersion` to it (BR-CON-002) --
    AI extraction (CON-003) is dispatched asynchronously either way."""
    data = await file.read()
    try:
        version = await contract_service.upload_contract_version(
            session,
            storage=storage,
            organization_id=user.organization_id,
            actor_id=user.id,
            supplier_id=supplier_id,
            filename=file.filename or "upload",
            data=data,
            contract_id=contract_id,
            title=title,
            contract_type=contract_type,
        )
    except tuple(_UPLOAD_ERROR_MAP) as exc:
        raise HTTPException(status_code=_UPLOAD_ERROR_MAP[type(exc)], detail=exc.message) from exc
    return _to_version_response(version)


@router.get("", response_model=list[ContractResponse])
async def list_contracts(user: CanReadContracts, session: SessionDep) -> list[ContractResponse]:
    contracts = await contract_service.list_contracts(session, organization_id=user.organization_id)
    return [ContractResponse.model_validate(c) for c in contracts]


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: uuid.UUID, user: CanReadContracts, session: SessionDep
) -> ContractResponse:
    try:
        contract = await contract_service.get_contract(
            session, organization_id=user.organization_id, contract_id=contract_id
        )
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return ContractResponse.model_validate(contract)


@router.get("/{contract_id}/versions", response_model=list[ContractVersionResponse])
async def list_contract_versions(
    contract_id: uuid.UUID, user: CanReadContracts, session: SessionDep
) -> list[ContractVersionResponse]:
    try:
        versions = await contract_service.list_contract_versions(
            session, organization_id=user.organization_id, contract_id=contract_id
        )
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return [_to_version_response(v) for v in versions]


@router.get(
    "/{contract_id}/versions/{version_id}",
    response_model=ContractVersionResponse,
)
async def get_contract_version(
    contract_id: uuid.UUID, version_id: uuid.UUID, user: CanReadContracts, session: SessionDep
) -> ContractVersionResponse:
    try:
        version = await contract_service.get_contract_version(
            session,
            organization_id=user.organization_id,
            contract_id=contract_id,
            version_id=version_id,
        )
    except (ContractNotFoundError, ContractVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return _to_version_response(version)


@router.get(
    "/{contract_id}/versions/{version_id}/clauses",
    response_model=list[ClauseResponse],
)
async def list_contract_version_clauses(
    contract_id: uuid.UUID, version_id: uuid.UUID, user: CanReadContracts, session: SessionDep
) -> list[ClauseResponse]:
    """CON-004: every clause carries its page/span citation (BR-CON-004)."""
    try:
        version = await contract_service.get_contract_version(
            session,
            organization_id=user.organization_id,
            contract_id=contract_id,
            version_id=version_id,
        )
    except (ContractNotFoundError, ContractVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    clauses = await ClauseRepository(session).list_by_contract_version(version.id)
    return [ClauseResponse.model_validate(c) for c in clauses]


@router.post(
    "/{contract_id}/versions/{version_id}/confirm",
    response_model=ContractVersionResponse,
)
async def confirm_contract_version(
    contract_id: uuid.UUID,
    version_id: uuid.UUID,
    body: ConfirmContractVersionRequest,
    user: CanUpdateContracts,
    session: SessionDep,
) -> ContractVersionResponse:
    """CON-005/BR-CON-003: confirms a `needs_confirmation` ContractVersion, unblocking
    `analyzed`. Backend endpoint only -- the confirmation UI itself is separate scope."""
    try:
        version = await contract_service.get_contract_version(
            session,
            organization_id=user.organization_id,
            contract_id=contract_id,
            version_id=version_id,
        )
    except (ContractNotFoundError, ContractVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc

    try:
        confirmed = await confirmation_service.confirm_contract_version(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            contract_version=version,
            corrections=body.corrections,
        )
    except ContractVersionNotReadyForConfirmationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return _to_version_response(confirmed)
