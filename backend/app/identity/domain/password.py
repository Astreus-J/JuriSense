"""Password strength policy."""

import re

from app.identity.domain.errors import WeakPasswordError

MIN_LENGTH = 8


def validate_password_strength(password: str) -> None:
    reasons: list[str] = []
    if len(password) < MIN_LENGTH:
        reasons.append(f"minimum of {MIN_LENGTH} characters")
    if not re.search(r"[a-z]", password):
        reasons.append("at least one lowercase letter")
    if not re.search(r"[A-Z]", password):
        reasons.append("at least one uppercase letter")
    if not re.search(r"\d", password):
        reasons.append("at least one digit")
    if reasons:
        raise WeakPasswordError(reasons)
