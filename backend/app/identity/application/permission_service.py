"""RBAC as data (ADR-003/ADR-012): seeds a new user's default permission grid and answers
effective "can this user do X on module Y" checks against the persisted grid — never a
hardcoded role branch.
"""

import logging
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.constants import Module, Role
from app.identity.domain.rbac import DEFAULT_ROLE_GRID
from app.identity.infrastructure.models import ModulePermission, User
from app.identity.infrastructure.repositories import ModulePermissionRepository

logger = logging.getLogger("jurisense.identity.permissions")

PermissionAction = Literal["create", "read", "update", "delete"]

_ACTION_FIELD: dict[PermissionAction, str] = {
    "create": "can_create",
    "read": "can_read",
    "update": "can_update",
    "delete": "can_delete",
}


async def seed_default_permissions(session: AsyncSession, *, user: User, role: Role) -> None:
    """Creates one `ModulePermission` row per module from `role`'s default grid.

    Called at every point a `User` is created (organization registration, admin-created
    user, invite acceptance) so the grid exists immediately — never lazily computed —
    matching ADR-012 ("permissions are a data lookup, not a code branch"). Does not commit;
    the caller's use case commits once at the end, same as every other `repository.add()`
    call in this context.
    """
    repository = ModulePermissionRepository(session)
    for module, permission in DEFAULT_ROLE_GRID[role].items():
        repository.add(
            ModulePermission(
                user_id=user.id,
                organization_id=user.organization_id,
                module=module.value,
                can_create=permission.can_create,
                can_read=permission.can_read,
                can_update=permission.can_update,
                can_delete=permission.can_delete,
            )
        )


async def reseed_permissions_for_role_change(
    session: AsyncSession, *, user: User, new_role: Role
) -> None:
    """Overwrites every existing `ModulePermission` row for `user` with `new_role`'s
    default grid, in place (mutates the persisted rows' can_create/read/update/delete
    fields rather than delete+recreate).

    Called whenever an admin changes a user's `role` (`user_service.update_user`).
    Without this, a demoted user keeps their old role's grid forever (a stale-privilege
    bug: an admin demoted to viewer would keep full CRUD indefinitely, since
    `has_permission` only ever reads the persisted grid, never re-derives it from the
    user's current `role`). Any per-user override an admin had granted beyond the old
    role's default (STORY-0.2.4) is intentionally reset by a role change too -- an
    override tailored to the old role has no guaranteed relationship to the new one, so
    re-provisioning clean defaults is the safer default; the admin can grant new
    overrides for the new role afterward if needed.
    """
    grid = DEFAULT_ROLE_GRID[new_role]
    existing = await ModulePermissionRepository(session).list_by_user(user.id, user.organization_id)
    by_module = {row.module: row for row in existing}
    for module, permission in grid.items():
        row = by_module.get(module.value)
        if row is None:
            # Shouldn't normally happen (every module gets a row at creation time), but
            # stay correct rather than silently skipping a module if one is ever missing.
            ModulePermissionRepository(session).add(
                ModulePermission(
                    user_id=user.id,
                    organization_id=user.organization_id,
                    module=module.value,
                    can_create=permission.can_create,
                    can_read=permission.can_read,
                    can_update=permission.can_update,
                    can_delete=permission.can_delete,
                )
            )
            continue
        row.can_create = permission.can_create
        row.can_read = permission.can_read
        row.can_update = permission.can_update
        row.can_delete = permission.can_delete


async def has_permission(
    session: AsyncSession, *, user: User, module: Module, action: PermissionAction
) -> bool:
    """Deny-by-default: a user with no persisted grid row for `module` is refused, never
    implicitly allowed (fail-closed, ADR-012).
    """
    grid_row = await ModulePermissionRepository(session).get_by_user_module(
        user.id, user.organization_id, module.value
    )
    if grid_row is None:
        return False
    return getattr(grid_row, _ACTION_FIELD[action])


@dataclass(frozen=True)
class PermissionBackfillResult:
    users_checked: int
    permissions_added: int
    skipped_invalid_role_user_ids: tuple[str, ...]
    failed_user_ids: tuple[str, ...]


async def backfill_missing_module_permissions(session: AsyncSession) -> PermissionBackfillResult:
    """#188: a `Module` added after a user already existed (e.g. `evidence`, added by the
    Evidence & Audit context) never gets a `ModulePermission` row for that user
    automatically -- only `seed_default_permissions` (user-creation time) and
    `reseed_permissions_for_role_change` (role-change time) populate the grid, so a user
    who never changed role and predates the new module keeps getting a fail-closed `403`
    on it forever, even an Admin. This is the one-off remedy: for every existing User,
    across every organization, adds whatever `ModulePermission` rows their current role's
    `DEFAULT_ROLE_GRID` default says they should have but don't yet.

    Idempotent (a user whose grid is already complete contributes 0) and additive only --
    never touches an existing row's values, so a prior per-user override (STORY-0.2.4)
    survives untouched; this only fills gaps, the same spirit as `reseed_permissions_for_
    role_change`'s own "shouldn't normally happen, but stay correct" fallback for a single
    missing row, generalized to every user and applied proactively rather than only on a
    role change. Commits per user (not once at the end), the same "one broken row never
    blocks the rest" shape `evidence_package_service.backfill_missing_packages` uses --
    not expected to ever fail here, but there is no reason to risk an all-or-nothing
    transaction across every user on the platform for a fix this low-risk.

    Found while first running this against the real dev database (2026-10-12): a legacy
    `role="director"` row predating #181's fix (that string was never a real `Role` value)
    -- `Role(user.role)` raising `ValueError` for ANY one bad row would otherwise abort
    the whole run before any other user's gaps got filled. Skipped and logged instead,
    named in `skipped_invalid_role_user_ids` so the caller can fix the row's `role` and
    re-run -- consistent with this function's own "one broken row never blocks the rest"
    design, now actually applied to this failure mode too, not just the hypothetical one
    the docstring originally described.

    Code review (2026-10-12): the per-user commit alone didn't actually give the "one
    broken row never blocks the rest" guarantee this docstring claims -- unlike
    `evidence_package_service.backfill_missing_packages` (the pattern this mirrors),
    nothing here caught a failed commit (e.g. a `ModulePermission` unique-constraint
    collision from a concurrent run touching the same user). Each user's add+commit is
    now its own try/except, rolling back and recording the id in `failed_user_ids`
    rather than aborting every user after the one that failed.

    No user-facing route calls this; run manually (e.g. via `uv run python -c "..."` or
    a future `scripts/` entry point, `#166`) once after deploying a new `Module`."""
    # Read every primitive this loop needs up front, as plain Python values -- a mid-loop
    # `session.rollback()` (the commit-failure path below) expires every ORM object still
    # attached to the session, including every other not-yet-processed `User` in this
    # list; touching `user.role`/`user.organization_id` on the next iteration after that
    # would otherwise force a lazy (sync) reload this async session can't perform inline.
    users = [
        (user.id, user.role, user.organization_id)
        for user in (await session.execute(select(User))).scalars()
    ]
    repository = ModulePermissionRepository(session)
    added = 0
    skipped: list[str] = []
    failed: list[str] = []
    for user_id, role_value, organization_id in users:
        try:
            role = Role(role_value)
        except ValueError:
            logger.warning(
                "Skipping permission backfill for user %s: unrecognized role %r",
                user_id,
                role_value,
            )
            skipped.append(str(user_id))
            continue
        existing_modules = {
            row.module for row in await repository.list_by_user(user_id, organization_id)
        }
        grid = DEFAULT_ROLE_GRID[role]
        user_added = 0
        for module, permission in grid.items():
            if module.value in existing_modules:
                continue
            repository.add(
                ModulePermission(
                    user_id=user_id,
                    organization_id=organization_id,
                    module=module.value,
                    can_create=permission.can_create,
                    can_read=permission.can_read,
                    can_update=permission.can_update,
                    can_delete=permission.can_delete,
                )
            )
            user_added += 1
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.exception("Permission backfill commit failed for user %s", user_id)
            failed.append(str(user_id))
            continue
        added += user_added
    return PermissionBackfillResult(
        users_checked=len(users),
        permissions_added=added,
        skipped_invalid_role_user_ids=tuple(skipped),
        failed_user_ids=tuple(failed),
    )
