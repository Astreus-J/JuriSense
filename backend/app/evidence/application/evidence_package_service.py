"""EvidencePackage assembly, retrieval, recomputation and backfill (EVD-001, EVD-002, BR-EVD-001;
docs/03-domain/evidence.md "How Evidence entities compose into an EvidencePackage").

## Design: assembly is synchronous and never commits
`assemble_evidence_package` runs inside `decision_service.create_decision_for_review`, after the
Decision row is flushed and before the caller commits. A Decision therefore never exists without
its package, and the package never exists without its Decision. It does not commit: the caller
owns the transaction.

## Design: idempotent, one package per Decision
`uq_evidence_packages_one_per_decision` enforces one package per Decision. Assembly first checks
for an existing package and returns it unchanged if one exists, so a re-run is a no-op (no leaves,
no audit event). A superseded Decision keeps its package.

## Design: leaves are the source of truth, the root is derived
Leaves are persisted first, then the root is computed from the persisted rows (not from in-memory
objects), so the stored `merkle_root` is what a later recomputation from the same rows yields.
The canonical encoding, leaf hash, ordering and tree rules live in `domain/merkle.py`.

## Leaf catalog (what each leaf's `payload` holds)
Payloads hold only ids, versions, enum values and SHA-256 commitments. No contract text, no
personal data (BR-EVD-002).
- `decision`: compliance_review_id, contract_version_id, status, supersedes_decision_id, created_at.
- `contract_version`: contract_id, supplier_id, version_number, document_id.
- `document`: content_hash (the SHA-256 stored at upload), mime_type, size_bytes.
- `ai_execution`: provider, model_name, prompt_version, extracted_at (from the extraction run
  persisted in `ContractVersion.extracted_data`). Omitted when no extraction run is recorded.
- `policy_version`: policy_id, version_number (every PolicyVersion pooled by the review).
- `rule_evaluation`: rule_id, rule_key, outcome, severity, approver_role, rationale_commitment.
- `contract_field`: one per normalized contract field, `commitment` = hash of {value, provenance}.
- `supplier_check`: one per SupplierCheck the review's rule evaluations referenced
  (`evidence_refs`): supplier_id, supplier_profile_id, sources_consulted, raw_results_commitment.
- `reviewer`: one per ApprovalRequest of the review: approver_role, step_number, status,
  resolved_by, resolved_at.

The evidence_refs path is what makes supplier checks historical: it is what the review actually
used, read from immutable rows, not "whatever check is current today".

## Errors
A missing review, contract version, document, or supplier check raises `EvidenceError`. Each is
a broken reference, which should be impossible: the caller's transaction is then rolled back, and
the Decision is never created without its package.
"""

import logging
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.application.evidence_service import (
    list_all_decision_facts,
    list_reviewers_for_review,
)
from app.approvals.domain.evidence import DecisionFacts, ReviewerRecord
from app.contracts.application.evidence_service import get_contract_version_evidence
from app.contracts.domain.evidence import ContractVersionEvidenceDTO
from app.evidence.application.audit_service import emit_audit_event
from app.evidence.domain.errors import EvidenceError, EvidencePackageNotFoundError
from app.evidence.domain.merkle import LeafInput, commitment, compute_merkle, leaf_hash
from app.evidence.infrastructure.models import AuditEvent, Evidence, EvidencePackage
from app.evidence.infrastructure.repositories import EvidencePackageRepository, EvidenceRepository
from app.policies.application.evidence_service import get_review_evidence
from app.policies.domain.evidence import ReviewEvidenceDTO
from app.suppliers.application.evidence_service import get_supplier_check_evidence

_SUPPLIER_PROFILE_SOURCE = "supplier_profile"


logger = logging.getLogger("jurisense.evidence.packages")


@dataclass(frozen=True)
class PackageView:
    package: EvidencePackage
    evidence: list[Evidence]


@dataclass(frozen=True)
class RecomputeResult:
    evidence_package_id: uuid.UUID
    stored_merkle_root: str
    recomputed_merkle_root: str
    matches: bool
    evidence_count: int
    mismatched_evidence_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class BackfillResult:
    considered: int
    created: int
    already_present: int
    failed_decision_ids: tuple[uuid.UUID, ...]


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.isoformat()


async def assemble_evidence_package(
    session: AsyncSession,
    *,
    facts: DecisionFacts,
    actor_id: uuid.UUID | None,
) -> EvidencePackage:
    """Creates the one EvidencePackage for `facts.decision_id`, or returns the existing one.
    Must be called after the Decision row is flushed. Does not commit."""
    repository = EvidencePackageRepository(session)
    existing = await repository.get_by_decision_and_organization(
        facts.decision_id, facts.organization_id
    )
    if existing is not None:
        return existing

    leaves = await _build_leaves(session, facts=facts)

    package = EvidencePackage(
        organization_id=facts.organization_id,
        decision_id=facts.decision_id,
        # Placeholder replaced below, once the persisted leaves exist to hash.
        merkle_root="",
        evidence_count=0,
        created_at=datetime.now(UTC),
    )
    repository.add(package)
    await session.flush()

    evidence_repository = EvidenceRepository(session)
    for leaf in leaves:
        evidence_repository.add(
            Evidence(
                organization_id=facts.organization_id,
                evidence_package_id=package.id,
                type=leaf.evidence_type,
                ref_id=leaf.ref_id,
                payload=dict(leaf.payload),
                content_hash=leaf_hash(leaf),
            )
        )
    await session.flush()

    persisted = await evidence_repository.list_by_package(package.id, facts.organization_id)
    merkle = compute_merkle(
        LeafInput(evidence_type=row.type, ref_id=row.ref_id, payload=row.payload)
        for row in persisted
    )
    package.merkle_root = merkle.root
    package.evidence_count = len(persisted)
    await session.flush()

    await emit_audit_event(
        session,
        event_type="evidence.package_created",
        actor_id=actor_id,
        organization_id=facts.organization_id,
        payload={
            "evidence_package_id": str(package.id),
            "decision_id": str(facts.decision_id),
            "evidence_count": package.evidence_count,
            "merkle_root": package.merkle_root,
            "created_at": _iso(package.created_at),
        },
    )
    return package


async def _build_leaves(session: AsyncSession, *, facts: DecisionFacts) -> list[LeafInput]:
    review = await get_review_evidence(
        session,
        organization_id=facts.organization_id,
        compliance_review_id=facts.compliance_review_id,
    )
    if review is None:
        raise EvidenceError("Cannot assemble evidence: compliance review not found")
    contract = await get_contract_version_evidence(
        session,
        organization_id=facts.organization_id,
        contract_version_id=facts.contract_version_id,
    )
    if contract is None:
        raise EvidenceError("Cannot assemble evidence: contract version or document not found")
    reviewers = await list_reviewers_for_review(
        session,
        organization_id=facts.organization_id,
        compliance_review_id=facts.compliance_review_id,
    )
    supplier_checks = await _supplier_check_leaves(
        session, organization_id=facts.organization_id, review=review
    )

    leaves = [
        _decision_leaf(facts),
        *_contract_leaves(contract),
        *_policy_and_rule_leaves(review),
        *_contract_field_leaves(contract),
        *supplier_checks,
        *(_reviewer_leaf(record) for record in reviewers),
    ]
    return leaves


def _decision_leaf(facts: DecisionFacts) -> LeafInput:
    return LeafInput(
        evidence_type="decision",
        ref_id=str(facts.decision_id),
        payload={
            "compliance_review_id": str(facts.compliance_review_id),
            "contract_version_id": str(facts.contract_version_id),
            "status": facts.status,
            "supersedes_decision_id": (
                str(facts.supersedes_decision_id) if facts.supersedes_decision_id else None
            ),
            "created_at": _iso(facts.created_at),
        },
    )


def _contract_leaves(contract: ContractVersionEvidenceDTO) -> list[LeafInput]:
    leaves = [
        LeafInput(
            evidence_type="contract_version",
            ref_id=str(contract.contract_version_id),
            payload={
                "contract_id": str(contract.contract_id),
                "supplier_id": str(contract.supplier_id),
                "version_number": contract.version_number,
                "document_id": str(contract.document_id),
            },
        ),
        LeafInput(
            evidence_type="document",
            ref_id=str(contract.document_id),
            payload={
                "content_hash": contract.document_content_hash,
                "mime_type": contract.document_mime_type,
                "size_bytes": contract.document_size_bytes,
            },
        ),
    ]
    if contract.extraction_run_id is not None:
        leaves.append(
            LeafInput(
                evidence_type="ai_execution",
                ref_id=contract.extraction_run_id,
                payload={
                    "provider": contract.extraction_provider,
                    "model_name": contract.extraction_model_name,
                    "prompt_version": contract.extraction_prompt_version,
                    "extracted_at": contract.extracted_at,
                },
            )
        )
    return leaves


def _policy_and_rule_leaves(review: ReviewEvidenceDTO) -> list[LeafInput]:
    leaves = [
        LeafInput(
            evidence_type="policy_version",
            ref_id=str(version.policy_version_id),
            payload={
                "policy_id": str(version.policy_id),
                "version_number": version.version_number,
            },
        )
        for version in review.policy_versions
    ]
    leaves.extend(
        LeafInput(
            evidence_type="rule_evaluation",
            ref_id=str(evaluation.rule_evaluation_id),
            payload={
                "rule_id": str(evaluation.rule_id),
                "rule_key": evaluation.rule_key,
                "outcome": evaluation.outcome,
                "severity": evaluation.severity,
                "approver_role": evaluation.approver_role,
                "rationale_commitment": commitment(evaluation.rationale),
            },
        )
        for evaluation in review.rule_evaluations
    )
    return leaves


def _contract_field_leaves(contract: ContractVersionEvidenceDTO) -> list[LeafInput]:
    return [
        LeafInput(
            evidence_type="contract_field",
            ref_id=field.context_path,
            payload={
                "commitment": commitment({"value": field.value, "provenance": field.provenance})
            },
        )
        for field in contract.fields
    ]


async def _supplier_check_leaves(
    session: AsyncSession, *, organization_id: uuid.UUID, review: ReviewEvidenceDTO
) -> list[LeafInput]:
    """One leaf per SupplierCheck the review's rule evaluations referenced. The profile id is
    taken from the same evidence_ref, so a check and its profile are always recorded together."""
    profile_by_check: dict[str, str] = {}
    for evaluation in review.rule_evaluations:
        for ref in evaluation.evidence_refs:
            if ref.get("source") != _SUPPLIER_PROFILE_SOURCE:
                continue
            check_id = ref.get("supplier_check_id")
            if check_id is not None:
                profile_by_check.setdefault(check_id, ref.get("supplier_profile_id"))

    leaves: list[LeafInput] = []
    for check_id, profile_id in sorted(profile_by_check.items()):
        check = await get_supplier_check_evidence(
            session,
            organization_id=organization_id,
            supplier_check_id=uuid.UUID(check_id),
        )
        if check is None:
            raise EvidenceError("Cannot assemble evidence: supplier check not found")
        leaves.append(
            LeafInput(
                evidence_type="supplier_check",
                ref_id=str(check.supplier_check_id),
                payload={
                    "supplier_id": str(check.supplier_id),
                    "supplier_profile_id": profile_id,
                    "sources_consulted": list(check.sources_consulted),
                    "raw_results_commitment": commitment(check.raw_results),
                },
            )
        )
    return leaves


def _reviewer_leaf(record: ReviewerRecord) -> LeafInput:
    return LeafInput(
        evidence_type="reviewer",
        ref_id=str(record.approval_request_id),
        payload={
            "approver_role": record.approver_role,
            "step_number": record.step_number,
            "status": record.status,
            "resolved_by": str(record.resolved_by) if record.resolved_by else None,
            "resolved_at": _iso(record.resolved_at),
        },
    )


async def get_package(
    session: AsyncSession, *, organization_id: uuid.UUID, package_id: uuid.UUID
) -> PackageView:
    package = await EvidencePackageRepository(session).get_by_id_and_organization(
        package_id, organization_id
    )
    if package is None:
        raise EvidencePackageNotFoundError()
    evidence = await EvidenceRepository(session).list_by_package(package.id, organization_id)
    return PackageView(package=package, evidence=evidence)


async def get_package_for_decision(
    session: AsyncSession, *, organization_id: uuid.UUID, decision_id: uuid.UUID
) -> PackageView:
    package = await EvidencePackageRepository(session).get_by_decision_and_organization(
        decision_id, organization_id
    )
    if package is None:
        raise EvidencePackageNotFoundError()
    evidence = await EvidenceRepository(session).list_by_package(package.id, organization_id)
    return PackageView(package=package, evidence=evidence)


async def recompute(
    session: AsyncSession, *, organization_id: uuid.UUID, package_id: uuid.UUID
) -> RecomputeResult:
    """BR-EVD-001: recomputes the root from the persisted Evidence rows only. Read-only: the
    stored `merkle_root` is never overwritten. `matches` is true only when the recomputed root
    equals the stored one AND the leaf count is unchanged."""
    package = await EvidencePackageRepository(session).get_by_id_and_organization(
        package_id, organization_id
    )
    if package is None:
        raise EvidencePackageNotFoundError()
    rows = await EvidenceRepository(session).list_by_package(package.id, organization_id)

    merkle = compute_merkle(
        LeafInput(evidence_type=row.type, ref_id=row.ref_id, payload=row.payload) for row in rows
    )
    mismatched = tuple(
        row.id
        for row in rows
        if leaf_hash(LeafInput(evidence_type=row.type, ref_id=row.ref_id, payload=row.payload))
        != row.content_hash
    )
    return RecomputeResult(
        evidence_package_id=package.id,
        stored_merkle_root=package.merkle_root,
        recomputed_merkle_root=merkle.root,
        matches=(
            merkle.root == package.merkle_root
            and len(rows) == package.evidence_count
            and not mismatched
        ),
        evidence_count=len(rows),
        mismatched_evidence_ids=mismatched,
    )


async def backfill_missing_packages(session: AsyncSession) -> BackfillResult:
    """One-off: creates a package for every Decision that predates EVD-001. Idempotent: a
    Decision that already has a package is counted as `already_present` and left untouched. Each
    package is committed on its own, so one broken Decision does not block the rest, and a
    concurrent run that wins the race counts as `already_present`. This is an entry use case, so
    it commits (unlike `assemble_evidence_package`)."""
    facts_list = await list_all_decision_facts(session)
    original_status = await _original_decision_statuses(session)
    created = 0
    already_present = 0
    failed: list[uuid.UUID] = []
    repository = EvidencePackageRepository(session)
    for facts in facts_list:
        if await repository.get_by_decision_and_organization(
            facts.decision_id, facts.organization_id
        ):
            already_present += 1
            continue
        # The Decision row's `status` is overwritten in place by an override, so the package
        # must record the outcome the Decision was created with (`decision.created`).
        facts = replace(facts, status=original_status.get(facts.decision_id, facts.status))
        try:
            await assemble_evidence_package(session, facts=facts, actor_id=None)
            await session.commit()
            created += 1
        except IntegrityError:
            await session.rollback()
            already_present += 1
        except Exception:
            await session.rollback()
            logger.exception("Evidence backfill failed for decision %s", facts.decision_id)
            failed.append(facts.decision_id)
    return BackfillResult(
        considered=len(facts_list),
        created=created,
        already_present=already_present,
        failed_decision_ids=tuple(failed),
    )


async def _original_decision_statuses(session: AsyncSession) -> dict[uuid.UUID, str]:
    """The outcome each Decision was created with, read from its `decision.created` audit event."""
    result = await session.execute(
        select(AuditEvent.payload).where(AuditEvent.event_type == "decision.created")
    )
    statuses: dict[uuid.UUID, str] = {}
    for (payload,) in result.all():
        decision_id = uuid.UUID(payload["decision_id"])
        statuses.setdefault(decision_id, payload["status"])
    return statuses
