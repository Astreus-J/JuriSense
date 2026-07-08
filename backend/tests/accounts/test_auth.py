import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.accounts.infrastructure.models import Acesso

REGISTRO = {
    "organizacao_nome": "Escritório Exemplo",
    "nome_completo": "Ana Silva",
    "email": "ana@exemplo.com",
    "senha": "SenhaForte1",
}


async def _register(client: httpx.AsyncClient, **campos: str) -> httpx.Response:
    return await client.post("/api/auth/register", json={**REGISTRO, **campos})


async def _login(
    client: httpx.AsyncClient, email: str = "ana@exemplo.com", senha: str = "SenhaForte1"
) -> httpx.Response:
    return await client.post("/api/auth/login", json={"email": email, "senha": senha})


# ---- Registro (1.4) ----


async def test_register_cria_org_e_admin(client: httpx.AsyncClient) -> None:
    response = await _register(client)

    assert response.status_code == 202
    assert "senha" not in response.text and "senha_hash" not in response.text

    await _login(client)
    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {(await _login(client)).json()['access_token']}"},
    )
    assert me.json()["email"] == "ana@exemplo.com"
    assert me.json()["perfil"] == "administrador"
    assert me.json()["ativo"] is True


async def test_register_email_duplicado_sem_enumeracao(client: httpx.AsyncClient) -> None:
    """MED-002: resposta idêntica exista o e-mail ou não."""
    primeira = await _register(client)
    segunda = await _register(client, organizacao_nome="Outro Escritório")

    assert primeira.status_code == segunda.status_code == 202
    assert primeira.json() == segunda.json()


async def test_register_email_normalizado(client: httpx.AsyncClient) -> None:
    await _register(client, email="ANA@EXEMPLO.COM")

    response = await _login(client, email="ana@exemplo.com")
    assert response.status_code == 200


async def test_register_senha_fraca(client: httpx.AsyncClient) -> None:
    response = await _register(client, senha="curta")

    assert response.status_code == 422
    assert "política de segurança" in response.json()["detail"]


# ---- Login (1.5) ----


async def test_login_retorna_tokens(client: httpx.AsyncClient) -> None:
    await _register(client)
    response = await _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


async def test_login_senha_errada_e_email_inexistente_mesma_resposta(
    client: httpx.AsyncClient,
) -> None:
    await _register(client)
    senha_errada = await _login(client, senha="SenhaErrada1")
    email_inexistente = await _login(client, email="nao-existe@exemplo.com")

    assert senha_errada.status_code == email_inexistente.status_code == 401
    assert senha_errada.json() == email_inexistente.json()


async def test_login_bloqueia_apos_5_falhas(client: httpx.AsyncClient) -> None:
    await _register(client)
    for _ in range(5):
        response = await _login(client, senha="SenhaErrada1")
        assert response.status_code == 401

    # Mesmo com a senha correta, a conta está bloqueada
    response = await _login(client)
    assert response.status_code == 429
    assert "Retry-After" in response.headers


# ---- Histórico de acessos (1.6) ----


async def test_login_registra_acessos(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker
) -> None:
    await _register(client)
    await _login(client)
    await _login(client, senha="SenhaErrada1")

    async with db_session_factory() as session:
        total = await session.scalar(select(func.count(Acesso.id)))
        sucessos = await session.scalar(
            select(func.count(Acesso.id)).where(Acesso.sucesso.is_(True))
        )
    assert total == 2
    assert sucessos == 1


# ---- Tokens: me, refresh, logout (1.5) ----


async def _tokens(client: httpx.AsyncClient) -> dict[str, str]:
    await _register(client)
    return (await _login(client)).json()


async def test_me_exige_token_valido(client: httpx.AsyncClient) -> None:
    tokens = await _tokens(client)

    sem_token = await client.get("/api/auth/me")
    token_invalido = await client.get(
        "/api/auth/me", headers={"Authorization": "Bearer nao-e-um-jwt"}
    )
    valido = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert sem_token.status_code == 401
    assert token_invalido.status_code == 401
    assert valido.status_code == 200
    assert valido.json()["email"] == "ana@exemplo.com"


async def test_refresh_token_nao_serve_como_access(client: httpx.AsyncClient) -> None:
    tokens = await _tokens(client)

    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert response.status_code == 401


async def test_refresh_rotaciona_e_invalida_o_anterior(client: httpx.AsyncClient) -> None:
    tokens = await _tokens(client)

    primeiro = await client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert primeiro.status_code == 200
    assert primeiro.json()["refresh_token"] != tokens["refresh_token"]

    # Reuso do refresh já consumido é rejeitado
    reuso = await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuso.status_code == 401


async def test_logout_revoga_access_e_refresh(client: httpx.AsyncClient) -> None:
    tokens = await _tokens(client)
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.post(
        "/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=auth
    )
    assert response.status_code == 204

    me = await client.get("/api/auth/me", headers=auth)
    assert me.status_code == 401

    refresh = await client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 401
