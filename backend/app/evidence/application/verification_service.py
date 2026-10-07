"""FEATURE-8.3 / STORY-8.3.1: the public, unauthenticated verification check
(`docs/06-blockchain/verification.md`). A visitor with no JuriSense account, no
organization context, and no session -- an external auditor, a counterparty, a hackathon
judge -- pastes a reference they already hold (a `Decision` id, printed on an exported
Decision Passport, or the raw `EvidencePackage.merkle_root` hash itself) and gets back one of
four plain-language outcomes, sourced only from already-immutable records.

## The privacy boundary this module exists to hold (docs/06-blockchain/privacy.md, BR-EVD-002)
`PublicVerificationResult` is deliberately the ENTIRE public surface: the hash, a status, an
anchor timestamp, the provider/network name, and the provider-native reference needed to
check independently. It never carries a supplier name, a contract title, an organization id,
a policy rule, or any other `EvidencePackage`/`Decision` this visitor didn't already name.
Every repository call this module makes is the deliberate, explicitly-named cross-tenant
exception documented on `EvidencePackageRepository.get_by_decision_id_any_organization` --
this module is the only caller of those methods anywhere in the product.

## Why "mismatch" can fire at all
Resolving a Decision id to a hash trusts this database's own `EvidencePackage.merkle_root`
column (the visitor's OWN independent recomputation from a copy of the evidence, per that
doc's step 3, is a check this module plays no part in -- it never needs to). "mismatch" is
what a SUBSEQUENT, already-anchored proof failing to match THAT column's current value would
mean: the stored hash changed after anchoring without a new anchor being submitted, which the
immutability invariants on `EvidencePackage` and the git-committed/server-attested proof both
say should be impossible. Surfacing it instead of silently reporting "verified" is exactly the
tamper-evidence signal `docs/06-blockchain/blockchain-purpose.md` says this whole layer exists
to provide.

## Why `evidence_hash` is shown even when no anchor exists (security review, 2026-10-07)
`verification.md`'s own flow shows the resolved hash (step 3, "Hash display") BEFORE the
on-chain check (step 4) runs at all, specifically so a visitor can compare it against their
own independent recomputation "without relying on JuriSense's resolution step." A review
flagged that this means "reference resolves, no anchor" and "reference doesn't resolve at
all" are distinguishable by payload (`evidence_hash` populated vs `null`), both reported as
`not_found`. That distinction is this doc's own documented design, not an oversight -- and
the practical exposure is negligible (a Decision id is a UUIDv4, ~2^122 search space; a
`merkle_root` is a salted SHA-256 digest; neither is a feasible enumeration target). Keeping
it is a deliberate choice over silently contradicting the spec, made explicit here rather
than only in a commit message.

## Why a provider failure never raises (security review, 2026-10-07)
`public_routes.py` promises exactly one HTTP status, 200, for every call -- the outcome is
always in the body, never the status code, so there is no status-code side channel at all.
A `get_proof` call failing (a transient `git`/subprocess error for the transparency log, or a
network error for Constellation once active) used to propagate as `AnchoringProviderError`,
uncaught here, surfacing as an unhandled 500 -- exactly the side channel the design promises
not to have. `_safe_get_proof` below is the one place that promise is kept.
"""

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.application.anchoring_service import get_provider_by_name
from app.evidence.domain.anchoring import AnchorProof, AnchorStatus
from app.evidence.domain.errors import AnchoringProviderError
from app.evidence.infrastructure.models import BlockchainAnchor
from app.evidence.infrastructure.repositories import (
    BlockchainAnchorRepository,
    EvidencePackageRepository,
)

logger = logging.getLogger("jurisense.evidence.verification")

VerificationStatus = Literal["verified", "mismatch", "pending", "not_found"]

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


@dataclass(frozen=True)
class PublicVerificationResult:
    status: VerificationStatus
    evidence_hash: str | None
    provider: str | None
    confirmed_at: str | None
    reference_url: str | None


_NOT_FOUND = PublicVerificationResult(
    status="not_found", evidence_hash=None, provider=None, confirmed_at=None, reference_url=None
)


async def verify_public_reference(
    session: AsyncSession, *, reference: str
) -> PublicVerificationResult:
    """`reference` is either a 64-hex-char `merkle_root` or a `Decision` id (any UUID
    format). Never raises for a malformed/unknown/unanchored reference -- `not_found` is a
    legitimate, common outcome (a typo, or a reference that predates the Trust Layer being
    enabled), not an error."""
    reference = reference.strip()

    if _HASH_PATTERN.match(reference):
        package = await EvidencePackageRepository(session).get_by_merkle_root_any_organization(
            reference.lower()
        )
    else:
        try:
            decision_id = uuid.UUID(reference)
        except ValueError:
            return _NOT_FOUND
        package = await EvidencePackageRepository(session).get_by_decision_id_any_organization(
            decision_id
        )

    if package is None:
        return _NOT_FOUND

    anchor = await BlockchainAnchorRepository(session).get_by_package_id_any_organization(
        package.id
    )
    if anchor is None or anchor.status == AnchorStatus.FAILED.value:
        return PublicVerificationResult(
            status="not_found",
            evidence_hash=package.merkle_root,
            provider=None,
            confirmed_at=None,
            reference_url=None,
        )

    proof = await _safe_get_proof(anchor)
    if proof is None:
        # The provider itself couldn't be reached/resolved -- not a verdict on the evidence,
        # so this must never be reported as "verified" or "mismatch". "pending" is the
        # closest honest label this interface has for "try again shortly."
        return PublicVerificationResult(
            status="pending",
            evidence_hash=package.merkle_root,
            provider=None,
            confirmed_at=None,
            reference_url=None,
        )

    if proof.status is not AnchorStatus.CONFIRMED:
        return PublicVerificationResult(
            status="pending",
            evidence_hash=package.merkle_root,
            provider=anchor.provider,
            confirmed_at=None,
            reference_url=proof.reference_url,
        )

    verified = await get_provider_by_name(anchor.provider).verify(package.merkle_root, proof)
    return PublicVerificationResult(
        status="verified" if verified else "mismatch",
        evidence_hash=package.merkle_root,
        provider=anchor.provider,
        confirmed_at=proof.confirmed_at,
        reference_url=proof.reference_url,
    )


async def _safe_get_proof(anchor: BlockchainAnchor) -> AnchorProof | None:
    """`None` on any provider failure -- a config/network/subprocess error, never a
    legitimate verification outcome. Logged server-side; never raised to the public route."""
    try:
        provider = get_provider_by_name(anchor.provider)
        return await provider.get_proof(anchor.anchor_ref)
    except AnchoringProviderError:
        logger.exception(
            "Public verification could not reach the anchoring provider for anchor %s", anchor.id
        )
        return None
