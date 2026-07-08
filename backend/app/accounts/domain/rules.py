"""Regras de validação do domínio (espelha domain/rules.py do protótipo Django)."""

from datetime import UTC, datetime

from app.accounts.domain.constants import UFS_BRASIL
from app.accounts.domain.errors import OabInvalidaError


def validar_formato_oab(oab: str, uf: str | None) -> None:
    if uf is None:
        raise OabInvalidaError("informe a UF da OAB")
    if uf.upper() not in UFS_BRASIL:
        raise OabInvalidaError(f"UF '{uf}' desconhecida")
    if not oab.isdigit() or not 1 <= len(oab) <= 8:
        raise OabInvalidaError("número deve conter apenas dígitos (até 8)")


def as_utc(dt: datetime) -> datetime:
    """Normaliza datetimes vindos do banco (SQLite devolve naive) para UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def expirado(expira_em: datetime) -> bool:
    return datetime.now(UTC) > as_utc(expira_em)
