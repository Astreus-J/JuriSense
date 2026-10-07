"""The last-resort `AnchoringProvider` fallback (docs/09-planning/risks.md risk 4): "a trivial
hash + timestamp signed by JuriSense's own key, published to a public, git-backed transparency
log." Active as the project's default today (`Settings.anchoring_provider`) because Constellation
DED credentials are not self-service -- see `docs/06-blockchain/anchoring-providers.md`'s spike
findings -- not because this is the preferred long-term choice.

## Non-negotiable labeling requirement (risks.md risk 4)
`provider_name` is `"transparency_log"`, never anything that could be mistaken for a real chain.
Every caller that renders `BlockchainAnchor.provider`/`AnchorProof` to a human (the Decision
Passport, the public verification page) MUST show this as a labeled fallback, not a blockchain
anchor -- that labeling lives in those display layers, not here, but this module's own naming is
the first line of defense against it being presented as something it is not.

## What "public" requires beyond this module
This module performs real, local `git` operations against `repo_path` -- `git init` (once),
appending a line to `entries.jsonl`, and a real commit per anchor, so the log genuinely has the
tamper-evidence property a git history provides (a rewritten past commit changes every
descendant's hash). What this module does NOT do is push `repo_path` to a public remote -- doing
that is an outward-facing action (creating or writing to a publicly reachable repository) this
module's own test suite has no business triggering on every run, and is the one step the
spike's report flags as needing the user's explicit go-ahead before this fallback's "public,
third-party-checkable" claim is actually true end to end. Until that push exists, this is an
honest, tamper-evident LOCAL log -- `provider_name`'s fallback labeling already covers this gap in
the product's own claims, so no caller is misled either way.

## Key management
`signing_key_path` is a single hex-encoded Ed25519 private key, generated once on first use and
reused after -- regenerating it would make every previously anchored entry unverifiable against
the new public key. It is deliberately NOT under `repo_path`: everything in `repo_path` is meant
to be published; the private key must never be. The public key is committed into the repo itself
(`PUBLIC_KEY.txt`) the first time the repo is created, so anyone who clones it can verify every
entry without any out-of-band key exchange.
"""

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.evidence.domain.anchoring import AnchorProof, AnchorStatus
from app.evidence.domain.errors import AnchoringProviderError
from app.evidence.domain.merkle import canonical_json

_ENTRIES_FILE = "entries.jsonl"
_PUBLIC_KEY_FILE = "PUBLIC_KEY.txt"
_GIT_AUTHOR_NAME = "JuriSense Gate Transparency Log"
_GIT_AUTHOR_EMAIL = "transparency-log@jurisense.local"


def _run_git(repo_path: Path, *args: str) -> str:
    try:
        result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no user-controlled command
            ["git", *args],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            # Inherits the real environment (PATH, etc.) -- only HOME and the GIT_* identity
            # vars are overridden, so this never reads or writes a real user's global git
            # config (~/.gitconfig) while still resolving the `git` binary normally.
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": _GIT_AUTHOR_NAME,
                "GIT_AUTHOR_EMAIL": _GIT_AUTHOR_EMAIL,
                "GIT_COMMITTER_NAME": _GIT_AUTHOR_NAME,
                "GIT_COMMITTER_EMAIL": _GIT_AUTHOR_EMAIL,
                "HOME": str(repo_path),
            },
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise AnchoringProviderError(f"transparency log git command failed: {exc.stderr}") from exc
    except FileNotFoundError as exc:
        raise AnchoringProviderError("transparency log: git is not installed") from exc


def _load_or_create_signing_key(key_path: Path) -> Ed25519PrivateKey:
    if key_path.exists():
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_path.read_text().strip()))
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes_raw()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(raw.hex())
    key_path.chmod(0o600)
    return key


def _entry_payload(evidence_hash: str, timestamp: str) -> bytes:
    return canonical_json({"evidence_hash": evidence_hash, "timestamp": timestamp})


class TransparencyLogAnchoringProvider:
    """FEATURE-8.1/8.2: the fallback `AnchoringProvider`. Submission and confirmation are the
    same step (a git commit either exists or it doesn't -- there is no async settlement to
    poll), so `submit_hash` already returns a `confirmed`-shaped result; `get_proof`/`verify`
    exist for interface parity with providers that do have a settlement delay."""

    provider_name = "transparency_log"

    def __init__(self, *, repo_path: str, signing_key_path: str) -> None:
        self._repo_path = Path(repo_path).resolve()
        self._key_path = Path(signing_key_path).resolve()
        self._signing_key = _load_or_create_signing_key(self._key_path)

    def _ensure_repo(self) -> None:
        self._repo_path.mkdir(parents=True, exist_ok=True)
        if (self._repo_path / ".git").exists():
            return
        _run_git(self._repo_path, "init", "--initial-branch=main")
        public_key_hex = self._signing_key.public_key().public_bytes_raw().hex()
        (self._repo_path / _PUBLIC_KEY_FILE).write_text(
            "JuriSense Gate transparency log -- fallback verification mechanism, not a\n"
            "blockchain anchor (docs/09-planning/risks.md risk 4).\n\n"
            f"Ed25519 public key (hex): {public_key_hex}\n"
        )
        _run_git(self._repo_path, "add", _PUBLIC_KEY_FILE)
        _run_git(self._repo_path, "commit", "-m", "Initialize transparency log public key")

    async def submit_hash(self, evidence_hash: str) -> str:
        self._ensure_repo()
        timestamp = datetime.now(UTC).isoformat()
        signature = self._signing_key.sign(_entry_payload(evidence_hash, timestamp))
        entry = {
            "evidence_hash": evidence_hash,
            "timestamp": timestamp,
            "signature": signature.hex(),
        }
        entries_path = self._repo_path / _ENTRIES_FILE
        with entries_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        _run_git(self._repo_path, "add", _ENTRIES_FILE)
        _run_git(self._repo_path, "commit", "-m", f"Anchor {evidence_hash}")
        return _run_git(self._repo_path, "rev-parse", "HEAD")

    async def get_proof(self, anchor_ref: str) -> AnchorProof:
        entry = self._find_entry_for_commit(anchor_ref)
        if entry is None:
            return AnchorProof(status=AnchorStatus.FAILED, confirmed_at=None, reference_url=None)
        committed_at = _run_git(self._repo_path, "show", "-s", "--format=%aI", anchor_ref)
        return AnchorProof(
            status=AnchorStatus.CONFIRMED,
            confirmed_at=committed_at,
            reference_url=None,  # populated once repo_path is pushed to a public remote
            raw={"commit": anchor_ref, **entry},
        )

    async def verify(self, evidence_hash: str, proof: AnchorProof) -> bool:
        if proof.status is not AnchorStatus.CONFIRMED:
            return False
        if proof.raw.get("evidence_hash") != evidence_hash:
            return False
        try:
            signature = bytes.fromhex(proof.raw["signature"])
            payload = _entry_payload(evidence_hash, proof.raw["timestamp"])
            self._public_key().verify(signature, payload)
        except (InvalidSignature, KeyError, ValueError):
            return False
        return True

    def _public_key(self) -> Ed25519PublicKey:
        return self._signing_key.public_key()

    def _find_entry_for_commit(self, anchor_ref: str) -> dict[str, str] | None:
        """QA review (2026-10-07): `entries.jsonl` is strictly append-only -- one line added
        and committed per `submit_hash` call -- so the entry a given revision actually added
        is always the file's LAST line as of that revision, full stop. The previous version
        scanned for a line matching the commit message's hash instead, which could
        misattribute an older entry's timestamp/signature to a later `anchor_ref` if the same
        `evidence_hash` ever appeared twice in the log; indexing the last line makes that
        structurally impossible rather than merely unlikely."""
        try:
            content = _run_git(self._repo_path, "show", f"{anchor_ref}:{_ENTRIES_FILE}")
        except AnchoringProviderError:
            return None
        lines = content.splitlines()
        if not lines:
            return None
        return json.loads(lines[-1])
