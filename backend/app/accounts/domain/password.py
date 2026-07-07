"""Política de força de senha (RF02)."""

import re

from app.accounts.domain.errors import SenhaFracaError

TAMANHO_MINIMO = 8


def validar_forca_senha(senha: str) -> None:
    motivos: list[str] = []
    if len(senha) < TAMANHO_MINIMO:
        motivos.append(f"mínimo de {TAMANHO_MINIMO} caracteres")
    if not re.search(r"[a-z]", senha):
        motivos.append("ao menos uma letra minúscula")
    if not re.search(r"[A-Z]", senha):
        motivos.append("ao menos uma letra maiúscula")
    if not re.search(r"\d", senha):
        motivos.append("ao menos um dígito")
    if motivos:
        raise SenhaFracaError(motivos)
