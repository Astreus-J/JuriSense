import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.db import SessionDep
from app.identity.api.deps import require_permission
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import User
from app.suppliers.api.schemas import (
    CreateSupplierRequest,
    SupplierCheckResponse,
    SupplierProfileResponse,
    SupplierResponse,
    UpdateSupplierStatusRequest,
)
from app.suppliers.application import check_service, supplier_service
from app.suppliers.domain.constants import SupplierStatus
from app.suppliers.domain.errors import (
    ApprovalRequiresCompletedCheckError,
    DuplicateSupplierError,
    InvalidStatusTransitionError,
    InvalidTaxIdError,
    SupplierNotFoundError,
    SupplierProfileNotFoundError,
)
from app.suppliers.infrastructure.repositories import (
    SupplierCheckRepository,
    SupplierProfileRepository,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

CanCreateSuppliers = Annotated[User, Depends(require_permission(Module.SUPPLIERS, "create"))]
CanReadSuppliers = Annotated[User, Depends(require_permission(Module.SUPPLIERS, "read"))]
CanUpdateSuppliers = Annotated[User, Depends(require_permission(Module.SUPPLIERS, "update"))]


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    body: CreateSupplierRequest, user: CanCreateSuppliers, session: SessionDep
) -> SupplierResponse:
    """SUP-001: registers a Supplier and triggers its initial SupplierCheck (SUP-002).
    BR-SUP-002 (unique tax_id + organization_id) surfaces as 409, not 500."""
    try:
        supplier = await supplier_service.create_supplier(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            legal_name=body.legal_name,
            tax_id=body.tax_id,
            jurisdiction=body.jurisdiction,
        )
    except DuplicateSupplierError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except InvalidTaxIdError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message
        ) from exc
    return SupplierResponse.model_validate(supplier)


@router.get("", response_model=list[SupplierResponse])
async def list_suppliers(
    user: CanReadSuppliers,
    session: SessionDep,
    status_filter: Annotated[SupplierStatus | None, Query(alias="status")] = None,
) -> list[SupplierResponse]:
    """Strictly scoped to the caller's own organization (STORY-2.2). `status` filters
    across all five lifecycle states."""
    suppliers = await supplier_service.list_suppliers(
        session,
        organization_id=user.organization_id,
        status=status_filter.value if status_filter else None,
    )
    return [SupplierResponse.model_validate(s) for s in suppliers]


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: uuid.UUID, user: CanReadSuppliers, session: SessionDep
) -> SupplierResponse:
    try:
        supplier = await supplier_service.get_supplier(
            session, organization_id=user.organization_id, supplier_id=supplier_id
        )
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return SupplierResponse.model_validate(supplier)


@router.patch("/{supplier_id}/status", response_model=SupplierResponse)
async def update_supplier_status(
    supplier_id: uuid.UUID,
    body: UpdateSupplierStatusRequest,
    user: CanUpdateSuppliers,
    session: SessionDep,
) -> SupplierResponse:
    """BR-SUP-003: rejects a move to `approved` without a completed SupplierCheck free
    of an open sanctions flag."""
    try:
        supplier = await supplier_service.update_supplier_status(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            supplier_id=supplier_id,
            new_status=body.status,
        )
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except (ApprovalRequiresCompletedCheckError, InvalidStatusTransitionError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return SupplierResponse.model_validate(supplier)


@router.post(
    "/{supplier_id}/recheck",
    response_model=SupplierCheckResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def recheck_supplier(
    supplier_id: uuid.UUID, user: CanUpdateSuppliers, session: SessionDep
) -> SupplierCheckResponse:
    """SUP-002: manual re-check request, e.g. before a renewal."""
    try:
        supplier = await supplier_service.get_supplier(
            session, organization_id=user.organization_id, supplier_id=supplier_id
        )
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    check = await check_service.trigger_check(session, supplier=supplier)
    return SupplierCheckResponse.model_validate(check)


@router.get("/{supplier_id}/profile", response_model=SupplierProfileResponse)
async def get_supplier_profile(
    supplier_id: uuid.UUID, user: CanReadSuppliers, session: SessionDep
) -> SupplierProfileResponse:
    """SUP-003: the normalized, current-state SupplierProfile -- registry status,
    corporate structure, and the sanctions_hit flag (SUP-004/BR-SUP-004) a
    Compliance/Procurement user needs on the supplier detail screen. 404 both when the
    supplier itself doesn't exist/isn't in the caller's organization, and when it exists
    but no check has completed successfully yet."""
    try:
        supplier = await supplier_service.get_supplier(
            session, organization_id=user.organization_id, supplier_id=supplier_id
        )
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    profile = await SupplierProfileRepository(session).get_current_by_supplier(supplier.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=SupplierProfileNotFoundError().message,
        )
    return SupplierProfileResponse.model_validate(profile)


@router.get("/{supplier_id}/checks", response_model=list[SupplierCheckResponse])
async def list_supplier_checks(
    supplier_id: uuid.UUID, user: CanReadSuppliers, session: SessionDep
) -> list[SupplierCheckResponse]:
    """SUP-005: full, immutable SupplierCheck history, most recent first."""
    try:
        supplier = await supplier_service.get_supplier(
            session, organization_id=user.organization_id, supplier_id=supplier_id
        )
    except SupplierNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    checks = await SupplierCheckRepository(session).list_by_supplier(supplier.id)
    return [SupplierCheckResponse.model_validate(c) for c in checks]
