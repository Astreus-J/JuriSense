"""Jurisdiction-specific tax identifier validation (SUP-001).

QA/security review (2026-09-29) found no format validation at all: a garbage `tax_id`
(e.g. `"x"`) was accepted, stored, and the verification pipeline treated the resulting
BrasilAPI 404 as a legitimate "not found" outcome rather than a data-quality rejection,
letting a supplier with no real identifier silently advance to `under_review`.

Only the Brazil pack (CNAE/jurisdiction packs elsewhere are future-epic scope, see
`docs/09-planning/pivot-migration.md`) has a defined checksum -- other jurisdictions get a
digit-count check only, since JuriSense Gate has no other jurisdiction pack yet.
"""

from app.suppliers.domain.errors import InvalidTaxIdError

_CNPJ_LENGTH = 14
_FIRST_WEIGHTS = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_SECOND_WEIGHTS = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _check_digit(digits: str, weights: tuple[int, ...]) -> str:
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights, strict=True))
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def _is_valid_cnpj(digits: str) -> bool:
    """Official CNPJ checksum (Receita Federal). Rejects same-digit strings
    (`"00000000000000"`, etc.) the checksum alone would not otherwise catch."""
    if len(digits) != _CNPJ_LENGTH or len(set(digits)) == 1:
        return False
    first = _check_digit(digits[:12], _FIRST_WEIGHTS)
    second = _check_digit(digits[:12] + first, _SECOND_WEIGHTS)
    return digits[12:] == first + second


def validate_tax_id(digits: str, *, jurisdiction: str) -> None:
    """`digits` is already normalized to digits-only (see `_normalize_tax_id`). Raises
    `InvalidTaxIdError` if the identifier's shape can't be real for its jurisdiction."""
    if jurisdiction == "BR":
        if not _is_valid_cnpj(digits):
            raise InvalidTaxIdError(
                "A Brazilian tax_id must be a valid 14-digit CNPJ (checksum failed)"
            )
        return
    # No other jurisdiction pack exists yet -- a minimal, non-empty digit sequence is all
    # that can be meaningfully required until one does.
    if not digits or not digits.isdigit():
        raise InvalidTaxIdError("tax_id must be a non-empty numeric identifier")
