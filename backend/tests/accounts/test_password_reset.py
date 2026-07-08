"""Recuperação de senha (RF02): token 1h single-use, sem enumeração, revoga sessões."""

import re

import httpx

from tests.conftest import CapturingEmailSender

REGISTRO = {
    "organizacao_nome": "Escritório Exemplo",
    "nome_completo": "Ana Silva",
    "email": "ana@exemplo.com",
    "senha": "SenhaForte1",
}


def _extrair_token(sender: CapturingEmailSender) -> str:
    corpo = sender.messages[-1]["body"]
    return re.search(r"token=([\w~.-]+)", corpo).group(1)


async def _preparar(client: httpx.AsyncClient, sender: CapturingEmailSender) -> str:
    await client.post("/api/auth/register", json=REGISTRO)
    await client.post("/api/auth/password/forgot", json={"email": REGISTRO["email"]})
    return _extrair_token(sender)


async def test_forgot_nao_revela_existencia(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/register", json=REGISTRO)

    existente = await client.post(
        "/api/auth/password/forgot", json={"email": REGISTRO["email"]}
    )
    inexistente = await client.post(
        "/api/auth/password/forgot", json={"email": "ninguem@exemplo.com"}
    )

    assert existente.status_code == inexistente.status_code == 202
    assert existente.json() == inexistente.json()


async def test_reset_troca_senha_e_notifica(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    token = await _preparar(client, sent_emails)

    response = await client.post(
        "/api/auth/password/reset", json={"token": token, "nova_senha": "NovaSenha22"}
    )
    assert response.status_code == 200

    senha_antiga = await client.post(
        "/api/auth/login", json={"email": REGISTRO["email"], "senha": REGISTRO["senha"]}
    )
    senha_nova = await client.post(
        "/api/auth/login", json={"email": REGISTRO["email"], "senha": "NovaSenha22"}
    )
    assert senha_antiga.status_code == 401
    assert senha_nova.status_code == 200

    # Notificação pós-alteração (RF02)
    assert "alterada" in sent_emails.messages[-1]["subject"].lower()


async def test_reset_token_single_use(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    token = await _preparar(client, sent_emails)
    await client.post(
        "/api/auth/password/reset", json={"token": token, "nova_senha": "NovaSenha22"}
    )

    reuso = await client.post(
        "/api/auth/password/reset", json={"token": token, "nova_senha": "OutraSenha33"}
    )
    assert reuso.status_code == 400


async def test_novo_pedido_invalida_token_anterior(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    token_antigo = await _preparar(client, sent_emails)
    await client.post("/api/auth/password/forgot", json={"email": REGISTRO["email"]})

    response = await client.post(
        "/api/auth/password/reset", json={"token": token_antigo, "nova_senha": "NovaSenha22"}
    )
    assert response.status_code == 400


async def test_reset_revoga_sessoes_antigas(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    """MED-001: refresh tokens emitidos antes da troca deixam de valer."""
    await client.post("/api/auth/register", json=REGISTRO)
    login = await client.post(
        "/api/auth/login", json={"email": REGISTRO["email"], "senha": REGISTRO["senha"]}
    )
    refresh_antigo = login.json()["refresh_token"]

    await client.post("/api/auth/password/forgot", json={"email": REGISTRO["email"]})
    token = _extrair_token(sent_emails)
    await client.post(
        "/api/auth/password/reset", json={"token": token, "nova_senha": "NovaSenha22"}
    )

    response = await client.post("/api/auth/refresh", json={"refresh_token": refresh_antigo})
    assert response.status_code == 401


async def test_reset_token_invalido(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/auth/password/reset",
        json={"token": "token-inexistente", "nova_senha": "NovaSenha22"},
    )
    assert response.status_code == 400
