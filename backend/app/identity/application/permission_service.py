"""RBAC as data (ADR-003/ADR-012): seeds a new user's default permission grid and answers
effective "can this user do X on module Y" checks against the persisted grid — never a
hardcoded role branch.
"""

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.domain.constants import Module, Role
from app.identity.domain.rbac import DEFAULT_ROLE_GRID
from app.identity.infrastructure.models import ModulePermission, User
from app.identity.infrastructure.repositories import ModulePermissionRepository

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
