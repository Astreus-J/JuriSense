import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import security
from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.rate_limit import RateLimiter, RateLimitExceededError, rate_limit_by_ip
from app.core.redis import RedisDep
from app.identity.application.permission_service import PermissionAction, has_permission
from app.identity.domain.constants import Module, Role
from app.identity.domain.ports import EmailSender
from app.identity.infrastructure.email import ConsoleEmailSender, SMTPEmailSender
from app.identity.infrastructure.models import User
from app.identity.infrastructure.repositories import UserRepository
from app.identity.infrastructure.token_store import TokenStore

_bearer = HTTPBearer(auto_error=False)

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_access_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    redis: RedisDep,
) -> dict[str, Any]:
    if credentials is None:
        raise _INVALID_CREDENTIALS
    try:
        payload = security.decode_token(credentials.credentials, security.ACCESS_TOKEN)
    except security.TokenError as exc:
        raise _INVALID_CREDENTIALS from exc
    if await TokenStore(redis).is_access_blocked(payload["jti"]):
        raise _INVALID_CREDENTIALS
    return payload


AccessPayload = Annotated[dict[str, Any], Depends(get_access_payload)]


async def get_current_user(payload: AccessPayload, session: SessionDep) -> User:
    user = await UserRepository(session).get_by_id(uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise _INVALID_CREDENTIALS
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


def require_permission(
    module: Module, action: PermissionAction
) -> Callable[..., Coroutine[Any, Any, User]]:
    """Dependency factory gating a route on the caller's persisted RBAC grid (role default
    + any per-user override, ADR-012) for one `module`/`action` pair — the generic
    replacement for hand-rolling a role check per route (STORY-1.1.2), modeled on
    `get_current_admin` above.

    Deny-by-default: a user with no persisted `ModulePermission` row for `module` is
    refused, never implicitly allowed (fail-closed, ADR-012). Tenant scoping is a *separate*
    concern this dependency does not replace: it only answers "is this action allowed for
    this user's own organization's grid" — every route still scopes its actual data queries
    by the caller's `organization_id` itself (see `docs/04-architecture/components.md`).

    Usage from any bounded context's `api/` layer, e.g. `app/suppliers/api/routes.py`::

        from app.identity.api.deps import require_permission
        from app.identity.domain.constants import Module

        @router.post("", response_model=SupplierResponse)
        async def create_supplier(
            body: CreateSupplierRequest,
            user: Annotated[User, Depends(require_permission(Module.SUPPLIERS, "create"))],
            session: SessionDep,
        ) -> SupplierResponse:
            ...
    """

    async def _dependency(user: CurrentUser, session: SessionDep) -> User:
        if not await has_permission(session, user=user, module=module, action=action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing '{action}' permission on '{module.value}'",
            )
        return user

    return _dependency


def rate_limit_by_organization(
    *, max_requests: int, window_seconds: int, key_prefix: str
) -> Callable[..., Coroutine[Any, Any, None]]:
    """Dependency factory for an AUTHENTICATED route that triggers a real external API call
    and/or a Celery task (#143) -- a coarser, per-`organization_id` abuse/cost backstop,
    separate from `require_permission`'s authorization check and from plan-limit enforcement
    (`ADR-014`, `BR-ORG-003`). Lives here, not in `app/core/rate_limit.py` (which only has
    `rate_limit_by_ip`, used for unauthenticated routes), because it depends on
    `CurrentUser` to resolve `organization_id` -- `app/core` must not depend on any bounded
    context. Combine with `require_permission` on the same route (both as separate `Depends`
    params); FastAPI resolves `CurrentUser` once per request and shares it across both.

    Usage::

        from app.identity.api.deps import rate_limit_by_organization

        @router.post("/{id}/recheck", status_code=202)
        async def recheck(
            id: uuid.UUID,
            user: Annotated[User, Depends(require_permission(Module.SUPPLIERS, "update"))],
            _: Annotated[None, Depends(rate_limit_by_organization(
                max_requests=settings.external_call_rate_limit_max_requests,
                window_seconds=settings.external_call_rate_limit_window_seconds,
                key_prefix="supplier_recheck",
            ))],
            session: SessionDep,
        ) -> ...:
            ...
    """

    async def _check(user: CurrentUser, redis: RedisDep) -> None:
        limiter = RateLimiter(redis, max_requests=max_requests, window_seconds=window_seconds)
        try:
            await limiter.hit(f"{key_prefix}:{user.organization_id}")
        except RateLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Try again later.",
                headers={"Retry-After": str(exc.retry_after_seconds)},
            ) from exc

    return _check


# Security audit (2026-10-12): per-IP backstop on Identity's own unauthenticated endpoints
# (register, forgot/reset password, accept-invite) -- `rate_limit_by_ip` already existed and
# is used for the public verification route (#112), but was never wired here even though
# each of these also does a deliberately slow Argon2id hash per call (register, reset) or a
# DB write with no other throttle (forgot-password, accept-invite). `login` keeps this too,
# independent of its existing per-EMAIL lockout (`LoginLockout`) -- a lockout keyed on one
# victim email does nothing against one attacker IP trying many different emails.
IdentityRateLimited = Annotated[
    None,
    Depends(
        rate_limit_by_ip(
            max_requests=get_settings().identity_rate_limit_max_requests,
            window_seconds=get_settings().identity_rate_limit_window_seconds,
            key_prefix="identity_public",
        )
    ),
]


def get_email_sender() -> EmailSender:
    if get_settings().smtp_host:
        return SMTPEmailSender()
    return ConsoleEmailSender()


EmailDep = Annotated[EmailSender, Depends(get_email_sender)]
