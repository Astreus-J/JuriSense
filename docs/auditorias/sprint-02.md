# Auditoria de Segurança — Sprint 2 (Accounts: gestão de usuários e recuperação de senha)

**Data:** 2026-07-08 · **Escopo:** código novo da Sprint 2 (recuperação de senha, convites, CRUD de usuários, serviço de e-mail, TokenStore com índice por usuário, normalização de DATABASE_URL) · **Método:** skill `security-review` (OWASP) + checklist do ritual de `docs/_legacy/implementation-plan.md`.

## Resumo

- **Achados:** 0 críticos, 0 altos, 3 baixos. **A Sprint 3 está desbloqueada.**
- **Os 2 médios da S1 foram corrigidos e verificados por teste:**
  - **MED-001 (revogação global de sessões):** o TokenStore agora mantém índice `auth:user-refresh:{user_id}`; redefinição de senha e desativação de conta revogam todos os refresh tokens do usuário (`test_reset_revoga_sessoes_antigas`).
  - **MED-002 (enumeração no registro):** `POST /api/auth/register` responde 202 com corpo idêntico exista o e-mail ou não; e-mail já cadastrado recebe aviso de tentativa (`test_register_email_duplicado_sem_enumeracao`).

## Achados

### [LOW-005] Endpoints de e-mail sem rate limiting (Baixo)

`/auth/register`, `/auth/password/forgot` e `/users/invites` disparam e-mails e podem ser usados para spam/flood (custo de SMTP, queima de reputação do domínio). Convites exigem admin; os outros dois são públicos. Mitigação já planejada: rate limiting global por IP na **Sprint 5** (tarefa 5.3). Sem dados em risco.

### [LOW-006] Convite revela que e-mail já tem conta — para admins (Baixo)

`POST /users/invites` responde 409 quando o e-mail já está cadastrado. Diferente do registro público, aqui o chamador é um admin autenticado de uma organização paga, e a mensagem é necessária para a UX de convite. Risco aceito; o rate limiting da S5 limita abuso em massa.

### [LOW-007] Aceite de convite não notifica quem convidou (Baixo)

Quando um convite é aceito, o admin não recebe confirmação — dificultaria detectar aceite por terceiro caso o link vaze. Melhoria de detecção, não vulnerabilidade direta: adicionar notificação por e-mail ao `convidado_por` (oportunístico).

## Verificações sem achados

- **Tokens de link (reset/convite):** 256 bits via `secrets.token_urlsafe(32)`; **apenas o hash SHA-256 é persistido** — vazamento do banco não expõe tokens válidos (mais forte que o protótipo Django, que guarda o token em claro). Single-use e com expiração (1h reset / 7d convite), verificados por teste; novo pedido invalida os anteriores.
- **Enumeração:** `password/forgot` responde 202 idêntico para e-mail existente/inexistente (testado); mensagens de reset não distinguem token inexistente/usado/expirado.
- **Escopo multi-tenant:** listagem/detalhe/edição/desativação sempre filtrados pela organização do admin; usuário de outra org retorna **404** (sem vazar existência — testado); convite aceito entra na organização do convite, nunca escolhida pelo payload.
- **Autorização:** todas as rotas de gestão exigem `CurrentAdmin` (403 para demais perfis, 401 sem token — testado); aceite de convite é público por design (o convidado ainda não tem conta), protegido pelo token.
- **Autoproteção do admin:** não desativa a própria conta nem altera o próprio perfil/status (testado) — evita lockout da organização.
- **Desativação:** revoga refresh tokens do usuário; access tokens morrem no próximo request (checagem de `ativo` no `get_current_user`); login de conta inativa responde o 401 genérico.
- **Limites do plano:** verificados na criação direta, na criação do convite e no aceite (o estado pode mudar entre convite e aceite); reativação de usuário também conta no limite (testado).
- **E-mails:** corpo texto puro (sem HTML → sem injeção de markup); SMTP com STARTTLS; credenciais só via env.
- **Segredos:** `backend/.env` (com a URL real do Neon) está no `.gitignore` e fora do índice do git; `.env.example` voltou ao placeholder; grep sem segredos no código; `uv lock --check` ok.
- **DATABASE_URL:** normalização converte formato libpq para asyncpg e ativa `prepared_statement_cache_size=0` em endpoints com pooler — evita erros de prepared statement sob PgBouncer (disponibilidade).

## Encaminhamentos

| Achado | Destino |
|--------|---------|
| LOW-005 rate limiting de e-mail | Sprint 5 (tarefa 5.3, já prevista) |
| LOW-006 409 no convite | Risco aceito (ação de admin) |
| LOW-007 notificar aceite de convite | Oportunístico |

**Pendências das auditorias anteriores:** LOW-001 a LOW-004 (S1) continuam com os destinos já registrados (S5/oportunístico).
