from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.redis import RedisDep
from app.identity.api.deps import AccessPayload, CurrentUser, EmailDep, IdentityRateLimited
from app.identity.api.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.identity.application import auth_service, password_service
from app.identity.domain.constants import Plan
from app.identity.domain.errors import (
    AccountLockedError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidPasswordResetTokenError,
    InvalidRefreshTokenError,
    UserInactiveError,
    WeakPasswordError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


_REGISTRATION_RECEIVED = "Registration received; check your email for next steps."


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def register(
    body: RegisterRequest, session: SessionDep, email_sender: EmailDep, _: IdentityRateLimited
) -> MessageResponse:
    """Identical response whether or not the email exists (MED-002: avoids enumeration).

    SEC (2026-10-08): `plan` is otherwise attacker-controlled on this public, unauthenticated
    endpoint, with no payment/entitlement gate anywhere in the codebase (`ADR-014` defers the
    real payment gateway) -- self-service registration could request `plan=enterprise` and
    get genuinely unlimited `user_limit`/`supplier_limit`/`storage_limit_gb`/
    `ai_execution_limit` (`None`, per `PLAN_LIMITS`) for free. `go-to-market.md`'s business
    model is explicitly founder-led sales, never self-serve, for any paid tier -- so
    self-registration in production must only ever produce a Starter organization; a
    sales-closed upgrade happens out-of-band (an operator calling `register_organization`
    directly, as today, until a proper internal tool exists). Dev/test keep `plan` flexible
    since fixtures across the suite legitimately need non-Starter orgs to test plan-limit
    enforcement.
    """
    plan = body.plan if get_settings().environment != "production" else Plan.STARTER
    try:
        await auth_service.register_organization(
            session,
            organization_name=body.organization_name,
            full_name=body.full_name,
            email=body.email,
            password=body.password,
            phone=body.phone,
            plan=plan,
        )
    except WeakPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{exc.message}: {', '.join(exc.reasons)}",
        ) from exc
    except EmailAlreadyRegisteredError:
        await email_sender.send(
            to=body.email.strip().lower(),
            subject="JuriSense — Registration attempt",
            body=(
                "Someone attempted to create a JuriSense account with this email, "
                "which is already registered. If this was you, log in or recover your password."
            ),
        )
        return MessageResponse(detail=_REGISTRATION_RECEIVED)
    return MessageResponse(detail=_REGISTRATION_RECEIVED)


@router.post(
    "/password/forgot", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED
)
async def forgot_password(
    body: ForgotPasswordRequest, session: SessionDep, email_sender: EmailDep, _: IdentityRateLimited
) -> MessageResponse:
    await password_service.request_password_reset(session, email_sender, email=body.email)
    return MessageResponse(detail="If the email is registered, we'll send a recovery link.")


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    session: SessionDep,
    redis: RedisDep,
    email_sender: EmailDep,
    _: IdentityRateLimited,
) -> MessageResponse:
    try:
        await password_service.reset_password(
            session, redis, email_sender, token=body.token, new_password=body.new_password
        )
    except WeakPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{exc.message}: {', '.join(exc.reasons)}",
        ) from exc
    except InvalidPasswordResetTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    return MessageResponse(detail="Password reset successfully.")


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: SessionDep,
    redis: RedisDep,
    _: IdentityRateLimited,
) -> TokenResponse:
    try:
        tokens = await auth_service.login(
            session,
            redis,
            email=body.email,
            password=body.password,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.message,
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except (InvalidCredentialsError, UserInactiveError) as exc:
        # Same response for a nonexistent user, wrong password, and an inactive account
        # (avoids user enumeration)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from exc
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: SessionDep, redis: RedisDep) -> TokenResponse:
    try:
        tokens = await auth_service.refresh_tokens(session, redis, refresh_token=body.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    return TokenResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, payload: AccessPayload, redis: RedisDep) -> None:
    await auth_service.logout(redis, access_payload=payload, refresh_token=body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
