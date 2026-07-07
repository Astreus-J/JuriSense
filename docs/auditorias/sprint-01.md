# Auditoria de Segurança — Sprint 1 (Accounts: fundação e autenticação)

**Data:** 2026-07-07 · **Escopo:** código novo da Sprint 1 (`app/core/security.py`, `app/core/config.py`, `app/core/redis.py`, `app/accounts/**`, Alembic, docker-compose) · **Método:** skill `security-review` (OWASP) + checklist do ritual definido em `docs/implementation-plan.md`.

## Resumo

- **Achados:** 2 médios, 4 baixos. Nenhum crítico ou alto — **a Sprint 2 está desbloqueada**.
- Os 2 médios viram tarefas na Sprint 2 (já relacionadas ao escopo dela).

## Achados

### [MED-001] Logout não encerra todas as sessões do usuário (Médio)

- **Local:** `app/accounts/application/auth_service.py` (`logout`) e `token_store.py`
- **Problema:** o logout revoga o access token e *o refresh token enviado no corpo* — que é opcional. Refresh tokens emitidos em outros logins (outros dispositivos, ou um token roubado) continuam válidos por até 7 dias; não existe índice `usuário → refresh jtis` para revogação em massa.
- **Impacto:** um refresh token comprometido sobrevive ao logout da vítima. Também impede o requisito da Sprint 2 de "revogar sessões antigas após troca de senha".
- **Correção:** manter um set `auth:user-refresh:{user_id}` com os jtis ativos; logout e troca de senha revogam todos. **→ tarefa da Sprint 2** (junto com 2.4, que já exige revogação de sessões).

### [MED-002] Enumeração de e-mails no registro (Médio)

- **Local:** `app/accounts/api/routes.py` (`POST /api/auth/register` → 409 "E-mail já cadastrado")
- **Problema:** login e (futuro) reset de senha não revelam se um e-mail existe, mas o registro revela, permitindo verificar em massa quais e-mails têm conta.
- **Impacto:** reconhecimento para phishing direcionado a advogados; contradiz o item "mensagens de erro sem enumeração" do checklist.
- **Correção:** na Sprint 2, quando houver serviço de e-mail (2.5), responder 202 genérico ("verifique seu e-mail") nos casos de conflito; até lá, o rate limiting da Sprint 5 mitiga a exploração em massa. **→ tarefa da Sprint 2.**

### [LOW-001] Política de senha mínima de 8 caracteres sem MFA (Baixo)

OWASP recomenda 15 sem MFA (ou 8 com MFA). O 2FA TOTP chega na Sprint 5. Decisão: manter 8 + composição por ora (UX de onboarding), reavaliar na S5 quando o MFA existir. Registrado como dívida consciente.

### [LOW-002] Bloqueio de conta utilizável como DoS contra usuários (Baixo)

5 senhas erradas bloqueiam qualquer e-mail por 15 min. Risco já previsto no plano (tabela de riscos); mitigação (bloqueio progressivo/CAPTCHA e rate limit por IP) é escopo da Sprint 5. Nota positiva: o 429 ocorre para e-mails inexistentes também, então não confirma existência de conta.

### [LOW-003] `INCR`/`EXPIRE` do lockout não são atômicos (Baixo)

`lockout.register_failure` faz `INCR` e depois `EXPIRE` (só na 1ª falha). Uma falha do processo entre os dois comandos deixa contador sem TTL (persistente até bloqueio manual). Corrigir oportunisticamente com pipeline/Lua ou `SET ... EX NX` + `INCR`.

### [LOW-004] IP registrado é o do peer TCP (Baixo)

`request.client.host` registrará o IP do Nginx/Cloudflare quando houver proxy na frente (produção na VPS). O histórico de acessos (RF01) perde valor forense. Tratar `X-Forwarded-For`/`CF-Connecting-IP` **apenas** quando emitido por proxy confiável — configurar junto com o Nginx (Sprint 5 / deploy).

## Verificações sem achados

- **Senhas:** Argon2id (argon2-cffi, parâmetros padrão ≥ recomendação OWASP); hash dummy no login para e-mails inexistentes (timing uniforme); senha nunca aparece em logs ou respostas.
- **JWT:** algoritmo fixado (`HS256`) na decodificação — sem confusão de algoritmo; claims obrigatórias (`sub`, `type`, `jti`, `exp`); tipos access/refresh não intercambiáveis (testado); refresh single-use com rotação (reuso → 401, testado); segredo só via env, com guard que impede subir produção com segredo dev/curto.
- **Enumeração no login:** mesma resposta 401 para senha errada, e-mail inexistente e conta inativa (testado).
- **Injeção:** 100% das queries via SQLAlchemy parametrizado; validação Pydantic (EmailStr, limites de tamanho) em todo input.
- **Segredos:** grep sem segredos hardcoded; `.env` no `.gitignore`; compose usa `${VAR:-default}`.
- **Dependências:** `uv lock --check` ok; libs de segurança são as canônicas (pyjwt, argon2-cffi).
- **LGPD:** dados pessoais novos: nome, e-mail, OAB (cadastro — necessários ao serviço) e histórico de acessos com IP/user-agent (RF01, base legal: segurança). Retenção do histórico a definir na S5 junto com RF06.

## Encaminhamentos

| Achado | Destino |
|--------|---------|
| MED-001 revogação global de sessões | Sprint 2 (junto à tarefa 2.4) |
| MED-002 enumeração no registro | Sprint 2 (junto à tarefa 2.5) |
| LOW-001 política de senha | Reavaliar na Sprint 5 (MFA) |
| LOW-002 lockout como DoS | Sprint 5 (rate limiting/CAPTCHA) |
| LOW-003 INCR/EXPIRE atômico | Oportunístico (qualquer sprint) |
| LOW-004 IP atrás de proxy | Sprint 5 / configuração do Nginx |
