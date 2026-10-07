"""FEATURE-8.1 (ADR-007 spike): unit tests for both concrete `AnchoringProvider` adapters,
independent of the application-layer `anchoring_service`/HTTP routes (`test_blockchain_
anchor.py` covers those). Each adapter is exercised against its own real mechanism --
real `git` for the fallback, a mocked HTTP transport for Constellation -- never against a
live network.
"""

import json
from pathlib import Path

import httpx
import pytest

from app.evidence.domain.anchoring import AnchorStatus
from app.evidence.domain.errors import AnchoringProviderError
from app.evidence.infrastructure.anchoring.constellation_provider import (
    ConstellationAnchoringProvider,
)
from app.evidence.infrastructure.anchoring.transparency_log_provider import (
    TransparencyLogAnchoringProvider,
)

HASH_A = "a" * 64
HASH_B = "b" * 64


def _transparency_log(tmp_path: Path) -> TransparencyLogAnchoringProvider:
    return TransparencyLogAnchoringProvider(
        repo_path=str(tmp_path / "repo"), signing_key_path=str(tmp_path / "key")
    )


class TestTransparencyLogAnchoringProvider:
    async def test_submit_then_verify_round_trip(self, tmp_path: Path) -> None:
        provider = _transparency_log(tmp_path)
        ref = await provider.submit_hash(HASH_A)

        proof = await provider.get_proof(ref)

        assert proof.status is AnchorStatus.CONFIRMED
        assert await provider.verify(HASH_A, proof) is True

    async def test_verify_rejects_a_different_hash_against_a_real_proof(
        self, tmp_path: Path
    ) -> None:
        provider = _transparency_log(tmp_path)
        ref = await provider.submit_hash(HASH_A)
        proof = await provider.get_proof(ref)

        assert await provider.verify(HASH_B, proof) is False

    async def test_verify_rejects_a_tampered_signature(self, tmp_path: Path) -> None:
        """Forces exactly the tamper this fallback exists to detect: the entry's recorded
        hash is swapped after the fact, without re-signing (what an attacker who could edit
        the file but not forge a signature would be limited to)."""
        provider = _transparency_log(tmp_path)
        ref = await provider.submit_hash(HASH_A)
        proof = await provider.get_proof(ref)

        tampered = proof.raw | {"evidence_hash": HASH_B}
        from dataclasses import replace

        tampered_proof = replace(proof, raw=tampered)

        assert await provider.verify(HASH_B, tampered_proof) is False

    async def test_get_proof_for_an_unknown_ref_is_failed_not_an_exception(
        self, tmp_path: Path
    ) -> None:
        provider = _transparency_log(tmp_path)
        await provider.submit_hash(HASH_A)  # ensures the repo exists

        proof = await provider.get_proof("0" * 40)

        assert proof.status is AnchorStatus.FAILED

    async def test_two_submissions_produce_two_distinct_commits(self, tmp_path: Path) -> None:
        provider = _transparency_log(tmp_path)
        ref_a = await provider.submit_hash(HASH_A)
        ref_b = await provider.submit_hash(HASH_B)

        assert ref_a != ref_b
        proof_a = await provider.get_proof(ref_a)
        proof_b = await provider.get_proof(ref_b)
        assert proof_a.raw["evidence_hash"] == HASH_A
        assert proof_b.raw["evidence_hash"] == HASH_B

    async def test_the_signing_key_persists_across_provider_instances(self, tmp_path: Path) -> None:
        """A restarted process must still be able to verify entries anchored before the
        restart -- regenerating the key on every instantiation would silently break that."""
        first = _transparency_log(tmp_path)
        ref = await first.submit_hash(HASH_A)

        second = _transparency_log(tmp_path)
        proof = await second.get_proof(ref)

        assert await second.verify(HASH_A, proof) is True

    async def test_repo_path_contains_a_committed_public_key_file(self, tmp_path: Path) -> None:
        """So anyone who clones the (eventually pushed) repo can verify entries without any
        out-of-band key exchange (this module's own docstring)."""
        provider = _transparency_log(tmp_path)
        await provider.submit_hash(HASH_A)

        public_key_file = tmp_path / "repo" / "PUBLIC_KEY.txt"
        assert public_key_file.exists()
        assert "not a" in public_key_file.read_text().lower()  # the fallback labeling


class TestConstellationAnchoringProvider:
    def _provider(
        self, handler: httpx.MockTransport, monkeypatch: pytest.MonkeyPatch
    ) -> ConstellationAnchoringProvider:
        import app.evidence.infrastructure.anchoring.constellation_provider as module

        monkeypatch.setattr(
            module,
            "_build_http_client",
            lambda timeout_seconds: httpx.AsyncClient(transport=handler),
        )
        return ConstellationAnchoringProvider(
            base_url="https://de-api.constellationnetwork.io/v1",
            api_key="test-key",
            org_id="11111111-1111-1111-1111-111111111111",
            tenant_id="22222222-2222-2222-2222-222222222222",
            private_key="11" * 32,  # a syntactically valid 64-hex-char SECP256K1 key
        )

    async def test_submit_hash_posts_a_signed_fingerprint_with_the_api_key_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json=[{"eventId": "e1", "hash": HASH_A, "accepted": True}])

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)
        ref = await provider.submit_hash(HASH_A)

        assert ref == HASH_A
        assert captured["headers"]["x-api-key"] == "test-key"
        [item] = captured["body"]
        assert item["attestation"]["content"]["documentRef"] == HASH_A
        assert item["attestation"]["content"]["orgId"] == "11111111-1111-1111-1111-111111111111"
        assert item["attestation"]["proofs"][0]["algorithm"] == "SECP256K1_RFC8785_V1"

    async def test_submit_hash_raises_when_the_api_rejects_the_submission(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=[{"eventId": "e1", "hash": HASH_A, "accepted": False, "errors": ["bad"]}]
            )

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)

        with pytest.raises(AnchoringProviderError):
            await provider.submit_hash(HASH_A)

    async def test_submit_hash_raises_on_a_non_200_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="unauthorized")

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)

        with pytest.raises(AnchoringProviderError):
            await provider.submit_hash(HASH_A)

    # The real response carries `hash` (a server-computed identifier for the whole signed
    # envelope -- also the `get_by_hash` lookup key and this adapter's `anchor_ref`) and
    # `documentRef` (what we actually submitted, our evidence hash) as two DISTINCT fields,
    # confirmed from the installed SDK's own `FingerprintDetail` type. Every mocked response
    # below gives them different values on purpose, so a `verify()` that compared the wrong
    # field would fail these tests instead of passing by coincidence.
    ENVELOPE_HASH = "e" * 64

    async def test_get_proof_maps_finalized_commitment_to_confirmed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "hash": self.ENVELOPE_HASH,
                        "documentRef": HASH_A,
                        "status": "FINALIZED_COMMITMENT",
                        "fingerprintTimestamp": "2026-10-07T00:00:00Z",
                    }
                },
            )

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)
        proof = await provider.get_proof(HASH_A)

        assert proof.status is AnchorStatus.CONFIRMED
        assert await provider.verify(HASH_A, proof) is True

    async def test_get_proof_maps_a_pending_status_to_submitted_not_confirmed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": {"hash": self.ENVELOPE_HASH, "documentRef": HASH_A, "status": "QUEUED"}
                },
            )

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)
        proof = await provider.get_proof(HASH_A)

        assert proof.status is AnchorStatus.SUBMITTED
        assert await provider.verify(HASH_A, proof) is False  # not confirmed yet

    async def test_get_proof_maps_errored_commitment_to_failed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "hash": self.ENVELOPE_HASH,
                        "documentRef": HASH_A,
                        "status": "ERRORED_COMMITMENT",
                    }
                },
            )

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)
        proof = await provider.get_proof(HASH_A)

        assert proof.status is AnchorStatus.FAILED

    async def test_get_proof_for_an_unknown_hash_is_failed_not_an_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"errors": [{"message": "not found"}]})

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)
        proof = await provider.get_proof(HASH_A)

        assert proof.status is AnchorStatus.FAILED

    async def test_get_proof_requires_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The GET endpoint is public per the API spec -- confirms this adapter never sends
        the API key on a lookup, matching docs/06-blockchain/verification.md's "no JuriSense
        backend involvement required" independence claim."""
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            return httpx.Response(
                200,
                json={
                    "data": {
                        "hash": self.ENVELOPE_HASH,
                        "documentRef": HASH_A,
                        "status": "FINALIZED_COMMITMENT",
                    }
                },
            )

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)
        await provider.get_proof(HASH_A)

        assert "x-api-key" not in captured["headers"]

    async def test_verify_rejects_a_hash_mismatch_even_when_confirmed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "hash": self.ENVELOPE_HASH,
                        "documentRef": HASH_B,
                        "status": "FINALIZED_COMMITMENT",
                    }
                },
            )

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)
        proof = await provider.get_proof(HASH_B)

        assert await provider.verify(HASH_A, proof) is False

    async def test_verify_does_not_mistake_the_envelope_hash_for_the_document_ref(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression for the exact bug a security review caught: `verify()` must compare
        against `documentRef`, not `hash` -- asserting against `HASH_A` (passed as the
        *envelope* hash here, with the real `documentRef` set to a different value) would
        wrongly return True if `verify()` ever reverts to checking the wrong field."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "hash": HASH_A,
                        "documentRef": HASH_B,
                        "status": "FINALIZED_COMMITMENT",
                    }
                },
            )

        provider = self._provider(httpx.MockTransport(handler), monkeypatch)
        proof = await provider.get_proof(HASH_A)

        assert await provider.verify(HASH_A, proof) is False
        assert await provider.verify(HASH_B, proof) is True
