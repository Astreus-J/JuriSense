"""Criação de usuários pela organização: só admin, própria org, limite do plano."""

import httpx

BASE_REGISTRO = {
    "organizacao_nome": "Escritório Exemplo",
    "nome_completo": "Ana Silva",
    "email": "ana@exemplo.com",
    "senha": "SenhaForte1",
}

NOVO_USUARIO = {
    "nome_completo": "Bruno Souza",
    "email": "bruno@exemplo.com",
    "senha": "OutraSenha1",
    "perfil": "advogado_junior",
}


async def _admin_headers(
    client: httpx.AsyncClient, plano: str = "escritorio", email: str = "ana@exemplo.com"
) -> dict[str, str]:
    """Registra uma organização e devolve o Authorization do admin logado."""
    await client.post(
        "/api/auth/register", json={**BASE_REGISTRO, "email": email, "plano": plano}
    )
    login = await client.post(
        "/api/auth/login", json={"email": email, "senha": BASE_REGISTRO["senha"]}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_criar_usuario_exige_autenticacao(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/users", json=NOVO_USUARIO)

    assert response.status_code == 401


async def test_admin_cria_usuario_na_propria_org(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    response = await client.post("/api/users", json=NOVO_USUARIO, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["perfil"] == "advogado_junior"
    assert body["email"] == "bruno@exemplo.com"

    me = await client.get("/api/auth/me", headers=headers)
    assert body["organizacao_id"] == me.json()["organizacao_id"]

    # O usuário criado consegue autenticar
    login = await client.post(
        "/api/auth/login", json={"email": "bruno@exemplo.com", "senha": "OutraSenha1"}
    )
    assert login.status_code == 200


async def test_nao_admin_nao_cria_usuario(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    await client.post("/api/users", json=NOVO_USUARIO, headers=headers)

    login = await client.post(
        "/api/auth/login", json={"email": "bruno@exemplo.com", "senha": "OutraSenha1"}
    )
    headers_junior = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post(
        "/api/users",
        json={**NOVO_USUARIO, "email": "carla@exemplo.com"},
        headers=headers_junior,
    )
    assert response.status_code == 403


async def test_limite_de_usuarios_do_plano(client: httpx.AsyncClient) -> None:
    # Plano autônomo: 1 usuário — o próprio admin já ocupa a vaga
    headers = await _admin_headers(client, plano="autonomo")

    response = await client.post("/api/users", json=NOVO_USUARIO, headers=headers)

    assert response.status_code == 402
    assert "autonomo" in response.json()["detail"]
    assert "upgrade" in response.json()["detail"]


async def test_perfil_invalido_rejeitado(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    response = await client.post(
        "/api/users", json={**NOVO_USUARIO, "perfil": "superadmin"}, headers=headers
    )
    assert response.status_code == 422


async def test_email_cpf_e_oab_duplicados(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    await client.post(
        "/api/users",
        json={**NOVO_USUARIO, "cpf": "111.222.333-44", "oab": "123456", "uf_oab": "SP"},
        headers=headers,
    )

    email_dup = await client.post("/api/users", json=NOVO_USUARIO, headers=headers)
    cpf_dup = await client.post(
        "/api/users",
        json={**NOVO_USUARIO, "email": "novo1@exemplo.com", "cpf": "111.222.333-44"},
        headers=headers,
    )
    oab_dup = await client.post(
        "/api/users",
        json={**NOVO_USUARIO, "email": "novo2@exemplo.com", "oab": "123456", "uf_oab": "SP"},
        headers=headers,
    )

    assert email_dup.status_code == 409
    assert cpf_dup.status_code == 409
    assert oab_dup.status_code == 409


async def test_payload_nao_escolhe_organizacao(client: httpx.AsyncClient) -> None:
    """organizacao_id no payload é ignorado: o destino é sempre a org do admin."""
    headers = await _admin_headers(client)

    response = await client.post(
        "/api/users",
        json={**NOVO_USUARIO, "organizacao_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )

    assert response.status_code == 201
    me = await client.get("/api/auth/me", headers=headers)
    assert response.json()["organizacao_id"] == me.json()["organizacao_id"]
