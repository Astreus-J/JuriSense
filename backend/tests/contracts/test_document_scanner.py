"""SEC-003: type-spoofing detection (true magic-byte sniffing vs. declared extension)
and the lightweight malware-signal checks (EICAR, executable/script magic bytes, size
limit) -- see `app.contracts.infrastructure.document_scanner`'s module docstring for the
explicit "no full AV engine yet" scope decision this test suite exercises.
"""

import io

import pytest
from docx import Document as DocxDocument

from app.contracts.domain.errors import (
    FileTooLargeError,
    MalwareDetectedError,
    UnsupportedFileTypeError,
)
from app.contracts.infrastructure.document_scanner import compute_content_hash, validate_and_scan

_MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
_EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def _make_docx_bytes() -> bytes:
    buf = io.BytesIO()
    doc = DocxDocument()
    doc.add_paragraph("This is a sample contract clause.")
    doc.save(buf)
    return buf.getvalue()


def test_valid_pdf_passes() -> None:
    mime = validate_and_scan(_MINIMAL_PDF, filename="contract.pdf", max_size_bytes=1_000_000)
    assert mime == "application/pdf"


def test_valid_docx_passes() -> None:
    data = _make_docx_bytes()
    mime = validate_and_scan(data, filename="contract.docx", max_size_bytes=1_000_000)
    assert mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_valid_txt_passes() -> None:
    mime = validate_and_scan(
        b"This is a plain text contract.", filename="contract.txt", max_size_bytes=1_000_000
    )
    assert mime == "text/plain"


def test_unsupported_extension_rejected() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_and_scan(b"whatever", filename="contract.xlsx", max_size_bytes=1_000_000)


def test_pe_executable_renamed_to_pdf_rejected() -> None:
    """The classic attack this control exists for: rename a Windows executable to
    `.pdf` and hope the server trusts the extension. Caught by the explicit
    executable-magic-byte denylist (checked before the mime-sniff allowlist), so this
    surfaces as `MalwareDetectedError` rather than `UnsupportedFileTypeError` -- either
    way, the upload never reaches storage."""
    exe_bytes = b"MZ" + b"\x90" * 200
    with pytest.raises(MalwareDetectedError):
        validate_and_scan(exe_bytes, filename="contract.pdf", max_size_bytes=1_000_000)


def test_shell_script_renamed_to_txt_rejected() -> None:
    script_bytes = b"#!/bin/sh\nrm -rf /\n"
    with pytest.raises(MalwareDetectedError):
        validate_and_scan(script_bytes, filename="notes.txt", max_size_bytes=1_000_000)


def test_docx_renamed_to_pdf_rejected_as_type_spoofing() -> None:
    """Cross-format spoofing within the "allowed" set is caught too, not just
    executable-vs-document."""
    data = _make_docx_bytes()
    with pytest.raises(UnsupportedFileTypeError):
        validate_and_scan(data, filename="contract.pdf", max_size_bytes=1_000_000)


def test_eicar_signature_rejected_as_malware_even_with_correct_extension() -> None:
    with pytest.raises(MalwareDetectedError):
        validate_and_scan(_EICAR, filename="contract.txt", max_size_bytes=1_000_000)


def test_pe_magic_bytes_rejected_as_malware_before_type_check() -> None:
    exe_bytes = b"MZ" + b"\x90" * 200
    with pytest.raises(MalwareDetectedError):
        validate_and_scan(exe_bytes, filename="contract.exe", max_size_bytes=1_000_000)


def test_oversized_file_rejected() -> None:
    with pytest.raises(FileTooLargeError):
        validate_and_scan(_MINIMAL_PDF, filename="contract.pdf", max_size_bytes=10)


def test_content_hash_is_deterministic_sha256() -> None:
    import hashlib

    expected = hashlib.sha256(_MINIMAL_PDF).hexdigest()
    assert compute_content_hash(_MINIMAL_PDF) == expected
    assert len(expected) == 64
