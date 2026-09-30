"""Upload validation & scanning (SEC-003) -- runs synchronously on every upload, before
any storage write or processing, per `docs/03-domain/contract-compliance.md` step 1
("the file is scanned for malware/type-spoofing before any content processing begins").

## Scope decision (explicit, not a silent under-scope)

SEC-003 asks for "malware/type-spoofing" validation. This module implements:

1. **Type-spoofing detection via true magic-byte sniffing** (`python-magic`/libmagic),
   never trusting the client-declared `Content-Type` header or the filename extension
   alone -- the sniffed type must match the declared extension, and only PDF/DOCX/TXT
   (the three formats `docs/05-ai/document-intelligence.md` supports) are accepted at
   all. This is real, load-bearing protection: it defeats "rename a .exe to .pdf" and
   "upload an HTML/script file with a .txt extension" style attacks, verified live above
   in this module's test suite against actual PE/ELF/shell-script/zip-bomb-shaped inputs.
2. **A lightweight, real malware signal, not a full AV engine**: the EICAR standard
   antivirus test string (industry-standard for verifying a scanner path is wired up at
   all) and an explicit executable/script magic-byte denylist checked before the
   mime-sniff allowlist even runs (clearer rejection reason, defense in depth).

**What this module deliberately does NOT do**: run a real signature-based/heuristic
antivirus engine (e.g. ClamAV) against arbitrary malicious payloads embedded inside an
otherwise well-formed PDF/DOCX (a malicious macro, an exploit-laden PDF object stream,
etc.). A full ClamAV daemon integration is new infrastructure -- a `docker-compose.yml`
service, a `ClamAVPort` abstraction, its own resource/ops footprint -- disproportionate
to what this phase needs to ship EPIC-3, and arguably deserves its own ADR given it is a
new architectural dependency, not a parameter tweak. This is a judgment call, stated
here explicitly per this epic's brief: **full AV-engine scanning is a documented `TBD`**
for a future phase (tracked alongside the other `TBD`s in `docs/05-ai/document-intelligence.md`),
not something this code silently pretends to already cover.
"""

import hashlib

import magic

from app.contracts.domain.errors import (
    FileTooLargeError,
    MalwareDetectedError,
    UnsupportedFileTypeError,
)

# The three formats document-intelligence.md supports -- anything else is rejected at
# upload time, "JuriSense Gate does not attempt best-effort parsing of arbitrary file
# types" (also a security boundary per that document's own cross-reference to SEC-003).
EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}

# EICAR standard antivirus test signature (https://www.eicar.org/) -- the industry
# convention for verifying a scanning path actually rejects something, without needing a
# real malicious sample. Split across a concatenation so this file itself is never
# mis-flagged as containing the signature by a real AV scanner running over this repo.
_EICAR_SIGNATURE = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$" b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)

# Explicit denylist checked first, ahead of the mime-sniff allowlist below, purely for a
# clearer rejection reason ("Windows executable" vs. a generic "unsupported type") --
# the allowlist in `_sniff_and_validate_type` is the actual backstop even if a variant of
# one of these isn't caught here.
_DENYLIST_PREFIXES: tuple[tuple[bytes, str], ...] = (
    (b"MZ", "Windows PE executable signature detected"),
    (b"\x7fELF", "ELF executable signature detected"),
    (b"#!", "script shebang signature detected"),
)


def _check_size(data: bytes, *, max_bytes: int) -> None:
    if len(data) > max_bytes:
        raise FileTooLargeError(max_bytes=max_bytes)


def _check_malware_signatures(data: bytes) -> None:
    if _EICAR_SIGNATURE in data:
        raise MalwareDetectedError(
            "Upload matches the EICAR test signature -- rejected as malware"
        )
    for prefix, reason in _DENYLIST_PREFIXES:
        if data.startswith(prefix):
            raise MalwareDetectedError(f"Upload rejected: {reason}")


def _extension_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


_SAFE_FILENAME_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
)


def safe_storage_filename(filename: str) -> str:
    """The filename component of an object-storage key must never be the raw
    client-supplied `filename` -- security review (2026-09-29): live-tested that
    `filename=../../../../etc/passwd.txt` was accepted outright, with no
    basename-stripping or character allowlist. S3-compatible keys are flat strings (no
    path resolution) and a fresh random `document_id` is always interposed before this
    component, so this wasn't independently exploitable for cross-object access -- but
    there was no defense at all against control characters, extreme lengths, or
    key-display log/CSV injection from an arbitrary filename. `original_filename` (the
    DB column used for display) keeps the raw, unsanitized value; only the *storage key*
    uses this.
    """
    basename = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    cleaned = "".join(ch if ch in _SAFE_FILENAME_CHARS else "_" for ch in basename)
    cleaned = cleaned.strip("._") or "upload"
    return cleaned[:200]


def _sniff_and_validate_type(data: bytes, *, filename: str) -> str:
    extension = _extension_of(filename)
    expected_mime = EXTENSION_TO_MIME.get(extension)
    if expected_mime is None:
        raise UnsupportedFileTypeError(
            f"Unsupported file extension '{extension}' -- only PDF/DOCX/TXT are accepted"
        )

    sniffed_mime = magic.from_buffer(data, mime=True)
    if sniffed_mime != expected_mime:
        # This is the type-spoofing case: the file's actual magic-byte-sniffed content
        # does not match what its extension/declared type claims to be.
        raise UnsupportedFileTypeError(
            f"File extension '{extension}' claims '{expected_mime}' but the file's actual "
            f"content sniffs as '{sniffed_mime}' -- rejected as a possible type-spoofing attempt"
        )
    return sniffed_mime


def validate_and_scan(data: bytes, *, filename: str, max_size_bytes: int) -> str:
    """Runs the full SEC-003 gate and returns the verified (sniffed, not declared) MIME
    type on success. Raises `FileTooLargeError` / `MalwareDetectedError` /
    `UnsupportedFileTypeError` otherwise -- never partially validates."""
    _check_size(data, max_bytes=max_size_bytes)
    _check_malware_signatures(data)
    return _sniff_and_validate_type(data, filename=filename)


def compute_content_hash(data: bytes) -> str:
    """SHA-256 hex digest -- computed once at upload, never recomputed
    (domain-model.md's `Document.content_hash` invariant)."""
    return hashlib.sha256(data).hexdigest()
