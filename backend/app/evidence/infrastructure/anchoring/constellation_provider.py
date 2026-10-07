"""The real `AnchoringProvider` adapter against Constellation Network's Digital Evidence
Depository (DED) -- the ADR-007 spike's chosen primary provider (`docs/06-blockchain/
anchoring-providers.md` §3). Live, documented REST API confirmed by hand on 2026-10-07:

    GET https://de-api.constellationnetwork.io/v1/fingerprints/<64 zero hex chars>
    -> 404 {"errors":[{"message":"... not found"}]}   (exactly as documented, no auth needed)

## Why this is the chosen adapter, not the generic EVM path
DED is purpose-built for exactly this use case ("create, sign, and submit cryptographic
fingerprints for document notarization"), has a first-party Python package
(`constellation-digital-evidence-sdk`, used below for the SECP256K1/RFC8785 signing this
module does not hand-roll), and -- critically -- `GET /fingerprints/{hash}` requires NO
authentication, which is exactly `docs/06-blockchain/verification.md`'s "independent, public,
JuriSense-uninvolved" check. The generic EVM L2 path (`docs/06-blockchain/smart-contracts.md`
Path A) remains available as a documented fallback if this adapter needs to be swapped.

## The actual spike finding: this is credential-blocked, not SDK-blocked
Submission (`POST /fingerprints`) requires an `X-API-Key` plus an `org_id`/`tenant_id` that
Constellation issues directly -- confirmed by reading the SDK's own quickstart ("provided by
Constellation") and the gitbook docs; there is no self-service signup page. This is the real,
concrete integration-effort finding `ADR-007`'s spike exists to produce: the SDK and the API
contract are both low-effort and well-documented (this adapter is the proof), but going live
needs a credential handoff from Constellation -- almost certainly through the hackathon's
sponsor channel, since Constellation is a listed Legal Hack 2026 sponsor. Until
`Settings.constellation_ded_*` are all set, `anchoring_service.get_provider` returns
`TransparencyLogAnchoringProvider` instead; this class is fully implemented and tested against
a mocked transport so flipping `anchoring_provider` to `"constellation"` the moment credentials
arrive is a config-only change, per every other provider-swap precedent in this codebase
(the AI Gateway's OpenRouter interim choice, ADR-005).
"""

import logging
import uuid

import httpx
from constellation_digital_evidence_sdk import DedSdkError, GenerateOptions, generate_fingerprint

from app.evidence.domain.anchoring import AnchorProof, AnchorStatus
from app.evidence.domain.errors import AnchoringProviderError

logger = logging.getLogger("jurisense.evidence.anchoring.constellation")

# QA review (2026-10-07): the installed SDK's own `FingerprintStatus` type
# (constellation_digital_evidence_sdk.network.types) is the authoritative vocabulary --
# UNASSIGNED | ASSIGNED | FINALIZED_COMMITMENT | ERRORED_COMMITMENT -- not the gitbook API
# spec text cited when this module was first written, which named a longer, unconfirmed
# set (NEW/QUEUED/PROCESSING/PENDING_COMMITMENT). Any status this adapter has not seen --
# including the two non-terminal ones above -- falls through to SUBMITTED below, so this
# was never a functional gap, only a comment worth getting right from the real source.
_FINALIZED_STATUSES = frozenset({"FINALIZED_COMMITMENT"})
_FAILED_STATUSES = frozenset({"ERRORED_COMMITMENT"})


def _build_http_client(timeout_seconds: float) -> httpx.AsyncClient:
    """Test seam: monkeypatched to return a client bound to `httpx.MockTransport`, the same
    pattern `app.integrations.infrastructure.cnpj_adapter._build_http_client` uses."""
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds, connect=5.0))


class ConstellationAnchoringProvider:
    """FEATURE-8.1/8.2: anchors a hash via Constellation's Digital Evidence Depository.

    `submit_hash` receives only the 32-byte hex `EvidencePackage.merkle_root` (BR-EVD-002) --
    it is passed as `GenerateOptions.document_ref` so the SDK's `generate_fingerprint` signs
    that exact value rather than hashing some other content (`create_fingerprint_value`'s
    documented behavior: `document_ref`, when given, is used as-is, never recomputed)."""

    provider_name = "constellation_digital_evidence"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        org_id: str,
        tenant_id: str,
        private_key: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._org_id = org_id
        self._tenant_id = tenant_id
        self._private_key = private_key
        # QA review (2026-10-07): Settings.constellation_ded_timeout_seconds was defined but
        # never actually read anywhere -- this is the one place it now flows through.
        self._timeout_seconds = timeout_seconds

    async def submit_hash(self, evidence_hash: str) -> str:
        # QA review (2026-10-07): wraps SDK signing too, not just the network call -- a
        # malformed `private_key` (SigningError/ValidationError, both DedSdkError) must
        # surface as this adapter's own documented error, not an unhandled exception.
        try:
            submission = generate_fingerprint(
                GenerateOptions(
                    org_id=self._org_id,
                    tenant_id=self._tenant_id,
                    event_id=str(uuid.uuid4()),
                    document_id=evidence_hash,
                    document_ref=evidence_hash,
                ),
                self._private_key,
            )
            body = [
                {
                    "attestation": {
                        "content": submission.attestation.content.to_dict(),
                        "proofs": [
                            {"id": p.id, "signature": p.signature, "algorithm": p.algorithm}
                            for p in submission.attestation.proofs
                        ],
                    },
                }
            ]
        except DedSdkError as exc:
            raise AnchoringProviderError(f"Constellation DED signing failed: {exc}") from exc

        async with _build_http_client(self._timeout_seconds) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/fingerprints",
                    json=body,
                    headers={"X-API-Key": self._api_key},
                )
            except httpx.HTTPError as exc:
                raise AnchoringProviderError(f"Constellation DED submission failed: {exc}") from exc

        if response.status_code != 200:
            raise AnchoringProviderError(
                f"Constellation DED submission returned HTTP {response.status_code}: "
                f"{response.text}"
            )
        # QA review: a 200 with an unexpected body shape must raise AnchoringProviderError,
        # not a raw ValueError/KeyError -- this is an external API's response, never
        # guaranteed to match the documented shape.
        try:
            [result] = response.json()
            accepted = result["accepted"]
            anchor_ref = result["hash"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AnchoringProviderError(
                f"Constellation DED submission returned an unexpected response shape: "
                f"{response.text}"
            ) from exc
        if not accepted:
            raise AnchoringProviderError(
                f"Constellation DED rejected submission: {result.get('errors')}"
            )
        return anchor_ref

    async def get_proof(self, anchor_ref: str) -> AnchorProof:
        async with _build_http_client(self._timeout_seconds) as client:
            try:
                response = await client.get(f"{self._base_url}/fingerprints/{anchor_ref}")
            except httpx.HTTPError as exc:
                raise AnchoringProviderError(f"Constellation DED lookup failed: {exc}") from exc

        if response.status_code == 404:
            return AnchorProof(status=AnchorStatus.FAILED, confirmed_at=None, reference_url=None)
        if response.status_code != 200:
            raise AnchoringProviderError(
                f"Constellation DED lookup returned HTTP {response.status_code}: {response.text}"
            )

        try:
            record = response.json()["data"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AnchoringProviderError(
                f"Constellation DED lookup returned an unexpected response shape: {response.text}"
            ) from exc
        status = record.get("status")
        if status in _FINALIZED_STATUSES:
            anchor_status = AnchorStatus.CONFIRMED
        elif status in _FAILED_STATUSES:
            anchor_status = AnchorStatus.FAILED
        else:
            anchor_status = AnchorStatus.SUBMITTED
        return AnchorProof(
            status=anchor_status,
            confirmed_at=record.get("fingerprintTimestamp")
            if anchor_status == AnchorStatus.CONFIRMED
            else None,
            reference_url=f"{self._base_url}/fingerprints/{anchor_ref}",
            raw=record,
        )

    async def verify(self, evidence_hash: str, proof: AnchorProof) -> bool:
        """Security review (2026-10-07): the installed SDK's own `FingerprintDetail` type
        (`constellation_digital_evidence_sdk.network.types`) carries `hash` and
        `document_ref` as two DISTINCT fields -- `hash` is a server-computed identifier for
        the whole signed envelope (also the value `get_by_hash`'s lookup key and this
        adapter's `anchor_ref` are), while `document_ref` is the value we actually submitted
        (`GenerateOptions.document_ref`, our evidence hash). Comparing against `hash` here
        would compare our hash against an unrelated server-generated one and permanently
        return `False` for every legitimately anchored package the moment this adapter is
        activated -- confirmed from the SDK's source, not assumed."""
        if proof.status is not AnchorStatus.CONFIRMED:
            return False
        return proof.raw.get("documentRef") == evidence_hash
