"""Portas do domínio: implementações concretas vivem na infraestrutura."""

from typing import Protocol


class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class OABValidator(Protocol):
    """Validação do registro na API da OAB (implementação real em fase posterior)."""

    async def is_registered(self, oab: str, uf: str) -> bool: ...
