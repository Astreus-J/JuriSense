"""CRUD de usuários (2.1/RF04): escopo da org, desativação lógica, OAB."""

import httpx

REGISTRO = {
    "organizacao_nome": "Escritório Exemplo",
    "nome_completo": "Ana Silva",
    "email": "ana@exemplo.com",
    "senha": "SenhaForte1",
    "plano": "escritorio",
}

NOVO = {
    "nome_completo": "Bruno Souza",
    "email": "bruno@exemplo.com",
    "senha": "SenhaForte2",
    "perfil": "advogado_junior",
}


async def _admin_headers(client: httpx.AsyncClient, email: str = "ana@exemplo.com") -> dict:
    await client.post(
        "/api/auth/register",
        json={**REGISTRO, "email": email, "organizacao_nome": f"Org de {email}"},
    )
    login = await client.post(
        "/api/auth/login", json={"email": email, "senha": REGISTRO["senha"]}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_listagem_escopada_por_organizacao(client: httpx.AsyncClient) -> None:
    headers_a = await _admin_headers(client, "admin-a@exemplo.com")
    headers_b = await _admin_headers(client, "admin-b@exemplo.com")
    await client.post("/api/users", json=NOVO, headers=headers_a)

    lista_a = (await client.get("/api/users", headers=headers_a)).json()
    lista_b = (await client.get("/api/users", headers=headers_b)).json()

    assert {u["email"] for u in lista_a} == {"admin-a@exemplo.com", "bruno@exemplo.com"}
    assert {u["email"] for u in lista_b} == {"admin-b@exemplo.com"}


async def test_get_usuario_de_outra_org_retorna_404(client: httpx.AsyncClient) -> None:
    headers_a = await _admin_headers(client, "admin-a@exemplo.com")
    headers_b = await _admin_headers(client, "admin-b@exemplo.com")
    criado = (await client.post("/api/users", json=NOVO, headers=headers_a)).json()

    proprio = await client.get(f"/api/users/{criado['id']}", headers=headers_a)
    alheio = await client.get(f"/api/users/{criado['id']}", headers=headers_b)

    assert proprio.status_code == 200
    assert alheio.status_code == 404


async def test_atualizar_usuario(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    criado = (await client.post("/api/users", json=NOVO, headers=headers)).json()

    response = await client.patch(
        f"/api/users/{criado['id']}",
        json={"nome_completo": "Bruno S. Atualizado", "perfil": "advogado_senior"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["nome_completo"] == "Bruno S. Atualizado"
    assert response.json()["perfil"] == "advogado_senior"


async def test_oab_invalida_rejeitada(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)

    sem_uf = await client.post(
        "/api/users", json={**NOVO, "oab": "123456"}, headers=headers
    )
    uf_errada = await client.post(
        "/api/users", json={**NOVO, "oab": "123456", "uf_oab": "XX"}, headers=headers
    )
    nao_numerica = await client.post(
        "/api/users", json={**NOVO, "oab": "ABC123", "uf_oab": "SP"}, headers=headers
    )

    assert sem_uf.status_code == 422
    assert uf_errada.status_code == 422
    assert nao_numerica.status_code == 422


async def test_desativacao_logica(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    criado = (await client.post("/api/users", json=NOVO, headers=headers)).json()

    response = await client.delete(f"/api/users/{criado['id']}", headers=headers)
    assert response.status_code == 204

    # Sem exclusão física: usuário continua listável, com status inativo
    detalhe = (await client.get(f"/api/users/{criado['id']}", headers=headers)).json()
    assert detalhe["status"] == "inativo"
    assert detalhe["ativo"] is False

    # E não autentica mais
    login = await client.post(
        "/api/auth/login", json={"email": NOVO["email"], "senha": NOVO["senha"]}
    )
    assert login.status_code == 401


async def test_admin_nao_desativa_a_si_mesmo(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    me = (await client.get("/api/auth/me", headers=headers)).json()

    response = await client.delete(f"/api/users/{me['id']}", headers=headers)
    assert response.status_code == 400


async def test_reativacao_respeita_limite_do_plano(client: httpx.AsyncClient) -> None:
    # Plano autônomo (1 usuário): reativar alguém além do admin deve falhar
    headers = await _admin_headers(client, "solo@exemplo.com")
    admin_org = await client.get("/api/auth/me", headers=headers)
    # Muda o plano manualmente não é possível via API; usa org escritorio e desativa até o limite
    headers = await _admin_headers(client, "cheia@exemplo.com")
    criados = []
    for i in range(4):
        r = await client.post(
            "/api/users",
            json={**NOVO, "email": f"membro{i}@exemplo.com"},
            headers=headers,
        )
        criados.append(r.json())
    # Org escritorio: 5 ativos (admin + 4). Desativa um e cria outro no lugar.
    await client.delete(f"/api/users/{criados[0]['id']}", headers=headers)
    r = await client.post(
        "/api/users", json={**NOVO, "email": "substituto@exemplo.com"}, headers=headers
    )
    assert r.status_code == 201

    # Reativar o desativado excederia o limite de 5
    reativar = await client.patch(
        f"/api/users/{criados[0]['id']}", json={"status": "ativo"}, headers=headers
    )
    assert reativar.status_code == 402
    assert admin_org.status_code == 200
