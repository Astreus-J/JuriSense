"""#188: `backfill_missing_module_permissions` -- a `Module` added after a user already
existed (the real incident: `evidence` was added post-pivot, after `Accounts`/Identity
users already existed) never gets a `ModulePermission` row for that user automatically,
so an existing Admin got a fail-closed 403 on every evidence route after that deploy.
"""

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.identity.application.permission_service import backfill_missing_module_permissions
from app.identity.domain.constants import Module
from app.identity.infrastructure.models import ModulePermission, User
from app.identity.infrastructure.repositories import ModulePermissionRepository, UserRepository
from tests.suppliers.conftest import register_org_and_login


async def test_backfill_adds_a_missing_module_row_using_the_user_s_current_role_default(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "backfill-admin@example.com")
    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("backfill-admin@example.com")
        admin_id, organization_id = admin.id, admin.organization_id
        # Simulates "this user predates the evidence module": its row never existed for
        # them, same end state as deleting it.
        await session.execute(
            delete(ModulePermission).where(
                ModulePermission.user_id == admin_id,
                ModulePermission.module == Module.EVIDENCE.value,
            )
        )
        await session.commit()

    async with db_session_factory() as session:
        before = await ModulePermissionRepository(session).get_by_user_module(
            admin_id, organization_id, Module.EVIDENCE.value
        )
    assert before is None

    async with db_session_factory() as session:
        result = await backfill_missing_module_permissions(session)
    assert result.permissions_added >= 1

    async with db_session_factory() as session:
        after = await ModulePermissionRepository(session).get_by_user_module(
            admin_id, organization_id, Module.EVIDENCE.value
        )
    assert after is not None
    # Admin's real default grid (rbac.py) grants full CRUD on evidence.
    assert after.can_create is True
    assert after.can_read is True


async def test_backfill_is_idempotent(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "backfill-idempotent@example.com")

    async with db_session_factory() as session:
        first = await backfill_missing_module_permissions(session)
    assert first.permissions_added == 0  # a freshly-registered user's grid is complete

    async with db_session_factory() as session:
        second = await backfill_missing_module_permissions(session)
    assert second.permissions_added == 0


async def test_backfill_never_touches_an_existing_per_user_override(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """Additive only (STORY-0.2.4 overrides survive): a row that already exists, even one
    an admin deliberately tweaked beyond the role default, must not be reset."""
    await register_org_and_login(client, "backfill-override@example.com")
    async with db_session_factory() as session:
        admin = await UserRepository(session).get_by_email("backfill-override@example.com")
        row = await ModulePermissionRepository(session).get_by_user_module(
            admin.id, admin.organization_id, Module.EVIDENCE.value
        )
        row.can_delete = True  # a deliberate per-user override beyond the role default
        await session.commit()

    async with db_session_factory() as session:
        await backfill_missing_module_permissions(session)

    async with db_session_factory() as session:
        after = await ModulePermissionRepository(session).get_by_user_module(
            admin.id, admin.organization_id, Module.EVIDENCE.value
        )
    assert after.can_delete is True  # untouched


async def test_backfill_skips_a_user_with_an_unrecognized_legacy_role_without_aborting(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    """Found running this for real against the dev database (2026-10-12): a legacy
    `role="director"` row predating #181's fix (never a real `Role` value) must not abort
    the whole backfill run -- every other user's gaps still get filled, and the bad row's
    id is reported back so it can be fixed and re-run."""
    await register_org_and_login(client, "backfill-good@example.com")
    await register_org_and_login(client, "backfill-bad-role@example.com")

    async with db_session_factory() as session:
        bad = await UserRepository(session).get_by_email("backfill-bad-role@example.com")
        bad.role = "director"  # the legacy, never-valid value
        await session.commit()
        bad_id = bad.id

        good = await UserRepository(session).get_by_email("backfill-good@example.com")
        await session.execute(
            delete(ModulePermission).where(
                ModulePermission.user_id == good.id,
                ModulePermission.module == Module.EVIDENCE.value,
            )
        )
        await session.commit()

    async with db_session_factory() as session:
        result = await backfill_missing_module_permissions(session)

    assert str(bad_id) in result.skipped_invalid_role_user_ids
    assert result.permissions_added >= 1  # the good user's gap was still filled

    async with db_session_factory() as session:
        filled = await ModulePermissionRepository(session).get_by_user_module(
            good.id, good.organization_id, Module.EVIDENCE.value
        )
    assert filled is not None


async def test_backfill_isolates_a_commit_failure_to_one_user_without_aborting(
    client: httpx.AsyncClient,
    db_session_factory: async_sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Code review (2026-10-12): per-user commit alone didn't give the "one broken row
    never blocks the rest" guarantee this function's docstring claims -- an uncaught
    commit failure for one user previously aborted every user after them too. Forces a
    real `IntegrityError` for one specific user deterministically (same "deterministic
    forced interleaving" approach `test_supplier_concurrency.py` uses for its own
    unreproducible race): monkeypatches `list_by_user` to report "nothing exists yet"
    for that one user only, so the backfill re-attempts inserting a row that already
    exists for them and collides with `uq_module_permission_user_module_org` at commit
    time -- while a second, unaffected user's real gap still gets filled."""
    await register_org_and_login(client, "backfill-fails@example.com")
    await register_org_and_login(client, "backfill-after-failure@example.com")

    async with db_session_factory() as session:
        failing = await UserRepository(session).get_by_email("backfill-fails@example.com")
        failing_id = failing.id
        after = await UserRepository(session).get_by_email("backfill-after-failure@example.com")
        await session.execute(
            delete(ModulePermission).where(
                ModulePermission.user_id == after.id,
                ModulePermission.module == Module.EVIDENCE.value,
            )
        )
        await session.commit()

    real_list_by_user = ModulePermissionRepository.list_by_user

    async def _lie_for_the_failing_user(self, user_id, organization_id):
        if user_id == failing_id:
            return []
        return await real_list_by_user(self, user_id, organization_id)

    monkeypatch.setattr(ModulePermissionRepository, "list_by_user", _lie_for_the_failing_user)

    async with db_session_factory() as session:
        result = await backfill_missing_module_permissions(session)

    assert str(failing_id) in result.failed_user_ids
    assert result.permissions_added >= 1  # the unaffected user's real gap was still filled

    async with db_session_factory() as session:
        filled = await ModulePermissionRepository(session).get_by_user_module(
            after.id, after.organization_id, Module.EVIDENCE.value
        )
    assert filled is not None


async def test_backfill_covers_every_organization_not_just_one(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await register_org_and_login(client, "backfill-org-a@example.com")
    await register_org_and_login(client, "backfill-org-b@example.com")

    async with db_session_factory() as session:
        for email in ("backfill-org-a@example.com", "backfill-org-b@example.com"):
            user = await UserRepository(session).get_by_email(email)
            await session.execute(
                delete(ModulePermission).where(
                    ModulePermission.user_id == user.id,
                    ModulePermission.module == Module.EVIDENCE.value,
                )
            )
        await session.commit()

    async with db_session_factory() as session:
        result = await backfill_missing_module_permissions(session)
    assert result.permissions_added == 2

    async with db_session_factory() as session:
        total_users = len((await session.execute(select(User))).scalars().all())
    assert result.users_checked == total_users
