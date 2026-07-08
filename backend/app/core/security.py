"""Hash de senha (Argon2id) e emissão/validação de JWT."""

import contextlib
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

ACCESS_TOKEN = "access"  # noqa: S105 — nome do tipo de token, não segredo
REFRESH_TOKEN = "refresh"  # noqa: S105

_hasher = PasswordHasher()  # parâmetros padrão do argon2-cffi (Argon2id)

# Hash de senha inexistente: mantém o tempo de resposta do login igual
# quando o e-mail não existe (evita enumeração por timing).
_DUMMY_HASH = _hasher.hash(uuid.uuid4().hex)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy_password(password: str) -> None:
    """Consome o mesmo tempo de um verify real; o resultado é sempre falha."""
    with contextlib.suppress(VerifyMismatchError, VerificationError, InvalidHashError):
        _hasher.verify(_DUMMY_HASH, password)


class TokenError(Exception):
    """Token ausente, inválido, expirado ou do tipo errado."""


def generate_opaque_token() -> tuple[str, str]:
    """Gera um token aleatório para links de e-mail.

    Retorna (token, hash): o token vai no link; apenas o hash SHA-256 é
    persistido, para que um vazamento do banco não exponha tokens válidos.
    """
    token = secrets.token_urlsafe(32)
    return token, hash_opaque_token(token)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _create_token(user_id: uuid.UUID, token_type: str, lifetime: timedelta) -> tuple[str, str]:
    settings = get_settings()
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + lifetime,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(user_id: uuid.UUID) -> tuple[str, str]:
    """Retorna (token, jti) com validade curta."""
    minutes = get_settings().access_token_expire_minutes
    return _create_token(user_id, ACCESS_TOKEN, timedelta(minutes=minutes))


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str]:
    """Retorna (token, jti) com validade longa; jti é registrado no Redis."""
    days = get_settings().refresh_token_expire_days
    return _create_token(user_id, REFRESH_TOKEN, timedelta(days=days))


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "type", "jti", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Token inválido ou expirado") from exc
    if payload["type"] != expected_type:
        raise TokenError("Tipo de token incorreto")
    return payload
