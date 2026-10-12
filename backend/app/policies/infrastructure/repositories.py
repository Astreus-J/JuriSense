import uuid
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.policies.infrastructure.models import (
    ComplianceReview,
    Policy,
    PolicyException,
    PolicyVersion,
    Risk,
    Rule,
    RuleEvaluation,
)


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

    async def count_by_organization(self, organization_id: uuid.UUID) -> int:
        """#180: backs `policy_service.create_policy`'s per-organization cap."""
        result = await self._session.execute(
            select(func.count())
            .select_from(Policy)
            .where(Policy.organization_id == organization_id)
        )
        return result.scalar_one()


class PolicyVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, version: PolicyVersion) -> None:
        self._session.add(version)

    async def get_by_id(self, version_id: uuid.UUID) -> PolicyVersion | None:
        return await self._session.get(PolicyVersion, version_id)

    async def list_by_ids_and_organization(
        self, version_ids: list[uuid.UUID], organization_id: uuid.UUID
    ) -> list[PolicyVersion]:
        """Tenant-scoped via the parent Policy (PolicyVersion carries no organization_id of its
        own). Used by the Evidence & Audit policy port, never for user-facing listings."""
        if not version_ids:
            return []
        result = await self._session.execute(
            select(PolicyVersion)
            .join(Policy, Policy.id == PolicyVersion.policy_id)
            .where(PolicyVersion.id.in_(version_ids), Policy.organization_id == organization_id)
        )
        return list(result.scalars())

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

    async def count_by_policy(self, policy_id: uuid.UUID) -> int:
        """#180: backs `policy_service.create_draft_version`'s per-policy version cap."""
        result = await self._session.execute(
            select(func.count())
            .select_from(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id)
        )
        return result.scalar_one()

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

    async def list_current_ids_by_organization(self, organization_id: uuid.UUID) -> set[uuid.UUID]:
        """The ids of every currently-published PolicyVersion in the organization -- the same
        pooling set `compliance_review_service.execute_review` evaluates against. Used by the
        re-evaluation staleness check (FEATURE-6.4, FEATURE-6.5): a review is stale when this
        set differs from the set it pooled, in either direction. Delegates to
        `list_current_by_organization` so the two sets cannot drift apart."""
        return {version.id for version in await self.list_current_by_organization(organization_id)}

    async def list_current_by_organization(self, organization_id: uuid.UUID) -> list[PolicyVersion]:
        """Every currently-published `PolicyVersion` across the whole organization -- one
        per `Policy` that has ever been published, at most, since `is_current` is only
        ever set `True` at publish time (`publish_service.publish_version`) and a `Policy`
        with no published version yet contributes none. This is the multi-policy pooling
        source for #123's trigger-review use case (see `ComplianceReview`'s module
        docstring for the design decision)."""
        result = await self._session.execute(
            select(PolicyVersion)
            .join(Policy, PolicyVersion.policy_id == Policy.id)
            .where(Policy.organization_id == organization_id, PolicyVersion.is_current.is_(True))
            .order_by(PolicyVersion.policy_id)
        )
        return list(result.scalars())


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

    async def count_by_version(self, policy_version_id: uuid.UUID) -> int:
        """#180: backs `rule_service.create_rule`'s per-version rule cap."""
        result = await self._session.execute(
            select(func.count())
            .select_from(Rule)
            .where(Rule.policy_version_id == policy_version_id)
        )
        return result.scalar_one()

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


class ComplianceReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, review: ComplianceReview) -> None:
        self._session.add(review)

    async def get_by_id_and_organization(
        self, review_id: uuid.UUID, organization_id: uuid.UUID
    ) -> ComplianceReview | None:
        result = await self._session.execute(
            select(ComplianceReview).where(
                ComplianceReview.id == review_id,
                ComplianceReview.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_contract_version(
        self, contract_version_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[ComplianceReview]:
        result = await self._session.execute(
            select(ComplianceReview)
            .where(
                ComplianceReview.contract_version_id == contract_version_id,
                ComplianceReview.organization_id == organization_id,
            )
            .order_by(ComplianceReview.started_at)
        )
        return list(result.scalars())

    async def count_superseding(self, decision_id: uuid.UUID, organization_id: uuid.UUID) -> int:
        """How many re-evaluation reviews were run against this Decision (FEATURE-6.5 attempt
        count). Counts reviews carrying `supersedes_decision_id == decision_id`, so the first
        re-evaluation counts too."""
        result = await self._session.execute(
            select(func.count(ComplianceReview.id)).where(
                ComplianceReview.supersedes_decision_id == decision_id,
                ComplianceReview.organization_id == organization_id,
            )
        )
        return int(result.scalar_one())


class RuleEvaluationRepository:
    """Append-only repository for `RuleEvaluation` (#126). Intentionally exposes only
    `add`/`get`/`list` -- no `update` or `delete` method exists anywhere on this class,
    mirroring `app.evidence.infrastructure.repositories.AuditEventRepository` exactly.
    This is the enforcement mechanism for BR-CMP-003: no actor, including an approver
    overriding a decision (a future EPIC-6 concern), has any path to modify or remove a
    recorded `RuleEvaluation` -- see `tests/policies/test_compliance_review.py`'s negative
    test."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, evaluation: RuleEvaluation) -> None:
        self._session.add(evaluation)

    async def get(self, evaluation_id: uuid.UUID) -> RuleEvaluation | None:
        return await self._session.get(RuleEvaluation, evaluation_id)

    async def list_by_review(self, compliance_review_id: uuid.UUID) -> list[RuleEvaluation]:
        result = await self._session.execute(
            select(RuleEvaluation)
            .where(RuleEvaluation.compliance_review_id == compliance_review_id)
            .order_by(RuleEvaluation.created_at)
        )
        return list(result.scalars())


class PolicyExceptionRepository:
    """Append-only (#120) -- exposes only `add`/`list_*`, no update/delete, mirroring
    `RuleEvaluationRepository`/`RiskRepository`: a `PolicyException` is left to expire
    via `valid_until`, never edited or revoked in place."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, exception: PolicyException) -> None:
        self._session.add(exception)

    async def list_by_rule(
        self, rule_id: uuid.UUID, *, organization_id: uuid.UUID
    ) -> list[PolicyException]:
        result = await self._session.execute(
            select(PolicyException)
            .where(
                PolicyException.rule_id == rule_id,
                PolicyException.organization_id == organization_id,
            )
            .order_by(PolicyException.created_at)
        )
        return list(result.scalars())

    async def count_active_for_rule(self, rule_id: uuid.UUID, *, now: datetime) -> int:
        """Backs `exception_service.grant_exception`'s per-rule cap -- counts currently
        active rows only (an expired exception no longer costs anything at evaluation
        time, so it doesn't count against the live cap)."""
        result = await self._session.execute(
            select(func.count())
            .select_from(PolicyException)
            .where(
                PolicyException.rule_id == rule_id,
                PolicyException.valid_from <= now,
                PolicyException.valid_until >= now,
            )
        )
        return result.scalar_one()

    async def list_active_for_rule_ids(
        self,
        rule_ids: list[uuid.UUID],
        *,
        organization_id: uuid.UUID,
        supplier_id: uuid.UUID | None,
        contract_version_id: uuid.UUID | None,
        now: datetime,
    ) -> list[PolicyException]:
        """Active exceptions (within `[valid_from, valid_until]`) for any of `rule_ids`,
        scoped to the organization and to the specific target the review is actually
        evaluating -- `supplier_id`/`contract_version_id` are matched only if the given
        arg is not `None`, since `execute_review`'s own call site may know only one of
        the two for a given contract/supplier pairing. Used by
        `compliance_review_service.execute_review` to build the rule_id -> exception
        lookup `evaluation_service.evaluate_policy_version` consumes."""
        if not rule_ids:
            return []
        target_clauses = []
        if supplier_id is not None:
            target_clauses.append(PolicyException.supplier_id == supplier_id)
        if contract_version_id is not None:
            target_clauses.append(PolicyException.contract_version_id == contract_version_id)
        if not target_clauses:
            return []
        # Code review (2026-10-12): nothing stops two overlapping active exceptions from
        # existing for the same rule+target (e.g. legal re-grants before the first
        # expires) -- `compliance_review_service.execute_review` builds a rule_id-keyed
        # dict from this list, so without a deterministic order, which grant's
        # justification/exception_id ends up cited on the RuleEvaluation would depend on
        # unspecified row order. Ascending `created_at` means the caller's
        # dict-comprehension (later entries overwrite earlier ones) deterministically
        # keeps the most recently granted exception.
        result = await self._session.execute(
            select(PolicyException)
            .where(
                PolicyException.organization_id == organization_id,
                PolicyException.rule_id.in_(rule_ids),
                PolicyException.valid_from <= now,
                PolicyException.valid_until >= now,
                or_(*target_clauses),
            )
            .order_by(PolicyException.created_at)
        )
        return list(result.scalars())


class RiskRepository:
    """Append-only repository for `Risk` -- exposes only `add`/`list`, mirroring
    `RuleEvaluationRepository`/`AuditEventRepository` (domain-model.md: "Invariants:
    immutable once created")."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, risk: Risk) -> None:
        self._session.add(risk)

    async def list_by_review(self, compliance_review_id: uuid.UUID) -> list[Risk]:
        result = await self._session.execute(
            select(Risk)
            .where(Risk.compliance_review_id == compliance_review_id)
            .order_by(Risk.created_at)
        )
        return list(result.scalars())
