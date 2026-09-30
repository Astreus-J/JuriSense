import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.policies.infrastructure.models import Policy, PolicyVersion, Rule


class PolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, policy: Policy) -> None:
        self._session.add(policy)

    async def get_by_id_and_organization(
        self, policy_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Policy | None:
        result = await self._session.execute(
            select(Policy).where(Policy.id == policy_id, Policy.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[Policy]:
        result = await self._session.execute(
            select(Policy)
            .where(Policy.organization_id == organization_id)
            .order_by(Policy.created_at)
        )
        return list(result.scalars())


class PolicyVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, version: PolicyVersion) -> None:
        self._session.add(version)

    async def get_by_id(self, version_id: uuid.UUID) -> PolicyVersion | None:
        return await self._session.get(PolicyVersion, version_id)

    async def get_by_id_and_policy(
        self, version_id: uuid.UUID, policy_id: uuid.UUID
    ) -> PolicyVersion | None:
        result = await self._session.execute(
            select(PolicyVersion).where(
                PolicyVersion.id == version_id, PolicyVersion.policy_id == policy_id
            )
        )
        return result.scalar_one_or_none()

    async def get_current_by_policy(self, policy_id: uuid.UUID) -> PolicyVersion | None:
        result = await self._session.execute(
            select(PolicyVersion).where(
                PolicyVersion.policy_id == policy_id, PolicyVersion.is_current.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_policy(self, policy_id: uuid.UUID) -> list[PolicyVersion]:
        result = await self._session.execute(
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id)
            .order_by(PolicyVersion.version_number.desc())
        )
        return list(result.scalars())

    async def get_next_version_number(self, policy_id: uuid.UUID) -> int:
        versions = await self.list_by_policy(policy_id)
        if not versions:
            return 1
        return versions[0].version_number + 1

    async def supersede_current(self, policy_id: uuid.UUID) -> None:
        """BR-POL-002: clears `is_current` on whatever version currently holds it for this
        policy -- mirrors `SupplierProfileRepository.replace_current`'s
        supersede-then-insert/set pattern. The caller sets the new current version's flag
        in the same transaction."""
        await self._session.execute(
            update(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id, PolicyVersion.is_current.is_(True))
            .values(is_current=False)
        )


class RuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, rule: Rule) -> None:
        self._session.add(rule)

    async def get_by_id(self, rule_id: uuid.UUID) -> Rule | None:
        return await self._session.get(Rule, rule_id)

    async def get_by_key_and_version(
        self, rule_key: str, policy_version_id: uuid.UUID
    ) -> Rule | None:
        result = await self._session.execute(
            select(Rule).where(
                Rule.policy_version_id == policy_version_id, Rule.rule_key == rule_key
            )
        )
        return result.scalar_one_or_none()

    async def list_by_version(self, policy_version_id: uuid.UUID) -> list[Rule]:
        result = await self._session.execute(
            select(Rule)
            .where(Rule.policy_version_id == policy_version_id)
            .order_by(Rule.created_at)
        )
        return list(result.scalars())

    def freeze(self, rules: list[Rule]) -> None:
        """BR-POL-001: flips `is_frozen` on every given (already-loaded) Rule -- called by
        `publish_service.publish_version` in the same transaction that publishes the
        owning `PolicyVersion`. `is_frozen` itself is not one of `Rule._guard_frozen`'s
        watched attributes, so this plain assignment is the one legitimate, one-time
        transition into the frozen state; every *other* field on these rows becomes
        unconditionally immutable from this point on. Operates on already-loaded ORM
        objects (rather than a bulk `UPDATE ... WHERE`) so the caller's in-memory `Rule`
        instances -- typically about to be serialized into the publish response/audit
        payload -- never go stale relative to what was actually persisted."""
        for rule in rules:
            rule.is_frozen = True
