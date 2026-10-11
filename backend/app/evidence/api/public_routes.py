"""FEATURE-8.3 / STORY-8.3.1: the ONE genuinely public, unauthenticated route in the Evidence
& Audit context (`docs/06-blockchain/verification.md`). Deliberately kept in its own module,
separate from `api/routes.py`'s tenant-scoped routes, so "this route has no `require_
permission` dependency" is a property of the FILE, not something a reviewer has to notice
line by line -- nothing here may ever gain a cross-tenant lookup that isn't already one of
`verification_service.verify_public_reference`'s own, explicitly-named exceptions.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.rate_limit import rate_limit_by_ip
from app.evidence.api.schemas import PublicVerificationResponse
from app.evidence.application.verification_service import verify_public_reference

public_router = APIRouter(prefix="/public", tags=["public-verification"])

_settings = get_settings()
RateLimited = Annotated[
    None,
    Depends(
        rate_limit_by_ip(
            max_requests=_settings.public_verification_rate_limit_max_requests,
            window_seconds=_settings.public_verification_rate_limit_window_seconds,
            key_prefix="public_verify",
        )
    ),
]


@public_router.get("/verify", response_model=PublicVerificationResponse)
async def verify(
    session: SessionDep,
    _: RateLimited,
    ref: str = Query(
        ..., min_length=1, max_length=255, description="A Decision id or an EvidencePackage hash."
    ),
) -> PublicVerificationResponse:
    """No authentication, no organization context -- by design, this is the one endpoint
    anyone on the internet can call. #112: IP-based rate limiting (`RateLimited` above) runs
    as a dependency before this body ever executes, so an over-limit caller gets a 429
    before `verify_public_reference` is reached at all. Always 200 otherwise:
    `not_found`/`pending`/`mismatch`/`verified` are the outcomes, never a 404/403, since
    there is no tenant boundary here to enforce or to leak through an error code."""
    result = await verify_public_reference(session, reference=ref)
    return PublicVerificationResponse.model_validate(result)
