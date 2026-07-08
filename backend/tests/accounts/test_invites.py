"""Convites (2.2): admin convida, convidado define senha, reenvio invalida o anterior."""

import re

import httpx

from tests.conftest import CapturingEmailSender

REGISTRO = {
    "organizacao_nome": "Escritório Exemplo",
    "nome_completo": "Ana Silva",
    "email": "ana@exemplo.com",
    "senha": "SenhaForte1",
    "plano": "escritorio",
}


def _token_do_ultimo_email(sender: CapturingEmailSender) -> str:
    return re.search(r"token=([\w~.-]+)", sender.messages[-1]["body"]).group(1)


async def _admin_headers(client: httpx.AsyncClient, plano: str = "escritorio") -> dict:
    await client.post("/api/auth/register", json={**REGISTRO, "plano": plano})
    login = await client.post(
        "/api/auth/login", json={"email": REGISTRO["email"], "senha": REGISTRO["senha"]}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _convidar(client: httpx.AsyncClient, headers: dict, **campos) -> httpx.Response:
    payload = {"email": "bruno@exemplo.com", "perfil": "advogado_junior", **campos}
    return await client.post("/api/users/invites", json=payload, headers=headers)


async def test_fluxo_completo_convite(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    headers = await _admin_headers(client)

    convite = await _convidar(client, headers)
    assert convite.status_code == 201
    assert convite.json()["status"] == "pendente"

    token = _token_do_ultimo_email(sent_emails)
    aceite = await client.post(
        "/api/users/accept-invite",
        json={"token": token, "senha": "SenhaForte2", "nome_completo": "Bruno Souza"},
    )
    assert aceite.status_code == 201
    assert aceite.json()["perfil"] == "advogado_junior"

    login = await client.post(
        "/api/auth/login", json={"email": "bruno@exemplo.com", "senha": "SenhaForte2"}
    )
    assert login.status_code == 200

    me = await client.get("/api/auth/me", headers=headers)
    assert aceite.json()["organizacao_id"] == me.json()["organizacao_id"]

    listagem = await client.get("/api/users/invites", headers=headers)
    assert listagem.json()[0]["status"] == "aceito"


async def test_convite_exige_admin(client: httpx.AsyncClient) -> None:
    sem_login = await client.post(
        "/api/users/invites", json={"email": "x@exemplo.com", "perfil": "estagiario"}
    )
    assert sem_login.status_code == 401


async def test_reenvio_invalida_convite_anterior(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    headers = await _admin_headers(client)

    await _convidar(client, headers)
    token_antigo = _token_do_ultimo_email(sent_emails)
    await _convidar(client, headers)  # reenvio

    aceite_antigo = await client.post(
        "/api/users/accept-invite",
        json={"token": token_antigo, "senha": "SenhaForte2", "nome_completo": "Bruno"},
    )
    assert aceite_antigo.status_code == 400


async def test_convite_token_single_use(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    headers = await _admin_headers(client)
    await _convidar(client, headers)
    token = _token_do_ultimo_email(sent_emails)

    payload = {"token": token, "senha": "SenhaForte2", "nome_completo": "Bruno"}
    primeiro = await client.post("/api/users/accept-invite", json=payload)
    segundo = await client.post("/api/users/accept-invite", json=payload)

    assert primeiro.status_code == 201
    assert segundo.status_code == 400


async def test_convite_respeita_limite_do_plano(
    client: httpx.AsyncClient, sent_emails: CapturingEmailSender
) -> None:
    # Plano autônomo: 1 usuário (o admin) — convite já barra na criação
    headers = await _admin_headers(client, plano="autonomo")

    convite = await _convidar(client, headers)
    assert convite.status_code == 402


async def test_convite_para_email_ja_cadastrado(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    convite = await _convidar(client, headers, email=REGISTRO["email"])
    assert convite.status_code == 409
