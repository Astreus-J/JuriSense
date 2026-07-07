# Plano de Implementação — Bounded Context Accounts

Usuários, autenticação, organizações, permissões e planos/assinaturas do JuriSense.

**Escopo:** RF01–RF06 do Módulo 1 (README) + fundação de planos/limites que suporta os 4 planos comerciais (Autônomo, Escritório, Escritório Plus, Enterprise — `frontend/src/lib/landing-data.ts`).

**Fora de escopo (fase posterior):** RF07 (SSO/SAML/SCIM), login com certificado ICP-Brasil, 2FA via SMS, integração com gateway de pagamento (Stripe/PagSeguro), validação real na API da OAB (entra como stub).

**Ritual fixo:** toda sprint termina com uma **auditoria de segurança** (seção "Auditoria por sprint" abaixo). Bug de segurança encontrado na auditoria bloqueia o início da sprint seguinte até ser corrigido.

---

## Arquitetura

Conforme `docs/IMPLEMENTACAO_ARQUITETURA/03_BACKEND_DDD.md` (adaptado a FastAPI): o contexto **Accounts** é o primeiro módulo DDD do backend.

- **Domínio:** entidades `Organizacao`, `Usuario`, `Perfil`, `Permissao`, `Plano`, `Assinatura`; regras puras (força de senha, bloqueio de tentativas, limites de plano) sem dependência de FastAPI/SQLAlchemy.
- **Aplicação:** casos de uso (registrar organização, autenticar, convidar usuário, trocar plano…) orquestrando repositórios.
- **Infraestrutura:** repositórios SQLAlchemy async (engine já existente em `app/core/db.py`), migrações Alembic, Redis para rate limiting e blocklist de tokens.
- **API:** rotas FastAPI finas sob `/api`, autorização via dependências (`CurrentUser`, `require_permission(...)`).
- **Multi-tenancy:** isolamento lógico por `organizacao_id` em todas as tabelas do tenant; toda query passa por repositório que exige o tenant — nunca filtro manual na rota.

### Estrutura de arquivos (alvo ao final das sprints)

```
backend/app/
├── core/
│   ├── config.py            # (existente) + settings de JWT/secrets
│   ├── db.py                # (existente)
│   └── security.py          # hash de senha, JWT encode/decode
├── accounts/
│   ├── domain/              # entidades, value objects, regras, erros
│   ├── application/         # casos de uso
│   ├── infrastructure/      # modelos ORM, repositórios, e-mail, redis
│   └── api/                 # rotas: auth, users, organizations, plans, permissions
├── api/router.py            # agrega as rotas do accounts
└── alembic/                 # migrações
backend/tests/accounts/      # testes por sprint
```

---

## Sprint 1 — Fundação: identidade e autenticação básica

**Objetivo:** uma organização se registra, o admin loga e recebe JWT; base de dados versionada.

| # | Tarefa | Critérios de aceite | Pontos |
|---|--------|---------------------|:------:|
| 1.1 | Alembic configurado com a `Base` de `app/core/db.py` | `alembic upgrade head` roda no compose; migração inicial gerada | 2 |
| 1.2 | Entidades e tabelas `organizacoes` e `usuarios` | Campos do RF04 (nome, e-mail único por org, OAB opcional), `ativo` para desativação lógica, timestamps | 3 |
| 1.3 | `core/security.py`: hash Argon2id + JWT (access 15min / refresh 7d) | Segredos só via env (`JWT_SECRET_KEY`); refresh rotativo; testes de expiração | 3 |
| 1.4 | Registro de organização + usuário admin | POST `/api/auth/register`; validação de força de senha (RF02); e-mail normalizado | 3 |
| 1.5 | Login, refresh e logout (RF01 parcial) | POST `/api/auth/login|refresh|logout`; bloqueio após 5 falhas (janela em Redis); resposta idêntica para "usuário não existe" e "senha errada" | 5 |
| 1.6 | Histórico de acessos (RF01) | Tabela `acessos` (usuário, IP, user-agent, timestamp, sucesso/falha) | 2 |
| 1.7 | **Auditoria de segurança S1** | Checklist da seção "Auditoria por sprint"; relatório em `docs/auditorias/sprint-01.md` | 3 |

**Total: 21 pontos** · Dependências: 1.1 → 1.2 → (1.4, 1.5); 1.3 → (1.4, 1.5); 1.5 → 1.6.

## Sprint 2 — Gestão de usuários e recuperação de senha

**Objetivo:** admin gerencia a equipe; fluxo de recuperação de senha completo. Cobre RF02 e RF04.

> Encaminhamentos da auditoria S1 (`docs/auditorias/sprint-01.md`): revogação global de sessões por usuário (MED-001, entra na 2.4) e resposta genérica no registro contra enumeração de e-mails (MED-002, entra na 2.5).
>
> Antecipado da 2.1/4.3 (espelhando o protótipo Django — TR-006): `POST /api/users` já existe — só admin autenticado cria usuários, sempre na própria organização, respeitando o limite de usuários do plano (org carrega `plano` + limites derivados; a Sprint 4 evolui isso para Assinatura). Restam na 2.1: listar/editar/desativar.

| # | Tarefa | Critérios de aceite | Pontos |
|---|--------|---------------------|:------:|
| 2.1 | CRUD de usuários (RF04) | Criar/listar/editar/desativar (sem DELETE físico); escopo sempre da organização do requisitante | 5 |
| 2.2 | Convite por e-mail com definição de senha | Token de convite single-use com expiração; reenvio invalida o anterior | 3 |
| 2.3 | Validação de OAB (stub com interface) | Porta `OABValidator` no domínio; implementação fake em dev; formato UF+número validado | 2 |
| 2.4 | Recuperação de senha (RF02) | Token expira em 1h, single-use; resposta não revela se o e-mail existe; notificação pós-alteração; sessões antigas revogadas | 5 |
| 2.5 | Serviço de e-mail (porta + adaptador console/dev) | Interface no domínio; adaptador SMTP configurável por env | 2 |
| 2.6 | **Auditoria de segurança S2** | Foco extra: enumeração de usuários, IDOR no CRUD, tokens de reset | 3 |

**Total: 20 pontos** · Dependências: Sprint 1 completa; 2.5 → (2.2, 2.4).

## Sprint 3 — Permissões e papéis (RBAC)

**Objetivo:** os 5 perfis do README funcionando com controle granular. Cobre RF03 e RF05 (parte de módulo+ação; permissão por processo individual fica para o contexto Processes).

| # | Tarefa | Critérios de aceite | Pontos |
|---|--------|---------------------|:------:|
| 3.1 | Seeds de permissões por perfil sobre a tabela `permissoes_modulo` (usuário × módulo × ação, criada na S1 espelhando o Django — TR-006) | Criar usuário com um dos 5 perfis (atores A01–A05 do README) materializa suas permissões padrão | 5 |
| 3.2 | Dependências de autorização FastAPI | `require_permission("modulo", "acao")` como dependência; negação → 403 com log; deny-by-default | 3 |
| 3.3 | Customização de permissões pelo admin (RF03) | Admin edita permissões de perfis não-admin da própria org; não pode remover o próprio acesso de admin | 3 |
| 3.4 | Endpoints de consulta | `GET /api/permissions/me` para o frontend montar a UI | 2 |
| 3.5 | Testes de matriz de acesso | Teste parametrizado perfil × endpoint cobrindo todos os endpoints existentes | 3 |
| 3.6 | **Auditoria de segurança S3** | Foco extra: escalada de privilégio, bypass de tenant (acessar dados de outra org), deny-by-default | 3 |

**Total: 19 pontos** · Dependências: Sprint 2 completa; 3.1 → 3.2 → (3.3, 3.4, 3.5).

## Sprint 4 — Planos, assinaturas e limites

**Objetivo:** os 4 planos comerciais modelados e seus limites aplicados. Sem cobrança real ainda — a assinatura tem estado (trial/ativa/inadimplente/cancelada), o pagamento entra depois via gateway.

| # | Tarefa | Critérios de aceite | Pontos |
|---|--------|---------------------|:------:|
| 4.1 | Entidades `Plano` e `Assinatura` + seeds | Autônomo, Escritório, Escritório Plus, Enterprise com limites (usuários, processos ativos, storage, gerações IA/mês) iguais à landing | 3 |
| 4.2 | Trial de 14 dias sem cartão | Registro cria assinatura trial; expiração → estado `expirada` degrada acesso (somente leitura) | 3 |
| 4.3 | Enforcement de limite de usuários | Criar usuário além do limite → 402/409 com mensagem de upgrade; verificação no caso de uso, não na rota | 3 |
| 4.4 | Contadores de uso (base p/ processos, storage, IA) | Tabela/serviço `uso_mensal` por org; interface para outros contextos incrementarem | 3 |
| 4.5 | Upgrade/downgrade de plano | Troca imediata com validação (downgrade bloqueado se uso atual excede o novo limite) | 3 |
| 4.6 | **Auditoria de segurança S4** | Foco extra: bypass de limites (race conditions em contadores), manipulação de assinatura por não-admin | 3 |

**Total: 18 pontos** · Dependências: Sprint 3 completa; 4.1 → (4.2, 4.3, 4.5); 4.4 → 4.5.

## Sprint 5 — Endurecimento: auditoria, 2FA e rate limiting

**Objetivo:** fechar RF06 e o restante do RF01; preparar o contexto para produção.

| # | Tarefa | Critérios de aceite | Pontos |
|---|--------|---------------------|:------:|
| 5.1 | Logs de auditoria (RF06) | Toda ação de escrita registra usuário, IP, timestamp, ação, antes/depois; tabela append-only (sem UPDATE/DELETE via app); retenção 5 anos documentada | 5 |
| 5.2 | 2FA TOTP (RF01) | Setup com QR code, códigos de recuperação, exigência configurável por org | 5 |
| 5.3 | Rate limiting global via Redis | Limites por IP e por usuário nos endpoints de auth; 429 com Retry-After | 3 |
| 5.4 | Security headers + hardening HTTP | HSTS, X-Content-Type-Options, CSP básica no Nginx/middleware; cookies `Secure`/`HttpOnly`/`SameSite` se usados | 2 |
| 5.5 | **Auditoria final do contexto Accounts** | Auditoria completa (não incremental): OWASP Top 10 sobre todo o contexto + revisão dos relatórios S1–S4 confirmando correções | 5 |

**Total: 20 pontos** · Dependências: Sprint 4 completa; 5.1–5.4 independentes entre si.

---

## Auditoria por sprint (ritual)

Executada como última tarefa de cada sprint, com relatório versionado em `docs/auditorias/sprint-NN.md`:

1. **Revisão automatizada:** rodar as skills `security-review` (revisão sistemática com OWASP) e `insecure-defaults` (segredos hardcoded, defaults inseguros) sobre o diff da sprint; `semgrep` quando disponível.
2. **Checklist manual mínimo:**
   - AuthN: senhas com Argon2id, tokens com expiração, mensagens de erro sem enumeração.
   - AuthZ: toda rota nova tem dependência de permissão; testes de matriz atualizados.
   - Multi-tenancy: nenhuma query sem `organizacao_id`; teste de acesso cruzado entre orgs.
   - Injeção: apenas queries parametrizadas (SQLAlchemy); validação Pydantic em todo input.
   - Segredos: nada hardcoded; `.env` fora do git; secrets só via env.
   - Dependências: `uv lock --check` + revisão de CVEs nas libs novas.
   - LGPD: dados pessoais novos mapeados (o que, por quê, retenção).
3. **Relatório:** achados classificados (crítico/alto/médio/baixo). Críticos e altos corrigidos **antes** da sprint seguinte; médios/baixos viram tarefas priorizadas.

## Caminho crítico

1.1 → 1.2 → 1.3 → 1.5 → 2.1 → 3.1 → 3.2 → 4.1 → 4.3 → 5.5 — a cadeia identidade → autorização → limites. As auditorias são gates entre sprints.

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| RBAC acoplado às rotas dificulta o RF05 completo (permissão por processo) | Alto | Modelo de permissão como dado (tabela), não como enum em código; dependência genérica `require_permission` |
| Race condition nos contadores de limite | Médio | Incremento atômico (UPDATE … RETURNING ou Redis INCR); teste de concorrência na auditoria S4 |
| Trial/assinatura sem gateway diverge do fluxo de pagamento futuro | Médio | Estados da assinatura desenhados a partir dos webhooks típicos de gateway (ativa/inadimplente/cancelada) |
| Logs de auditoria com dados pessoais (LGPD) vs. retenção de 5 anos | Médio | Campo antes/depois criptografado; política de acesso restrita ao admin |
| Bloqueio de conta (5 falhas) permite DoS contra usuários | Baixo | Bloqueio progressivo por IP+conta com janela curta; CAPTCHA como evolução |

## Mapeamento RF → Sprint

| RF | Descrição | Sprint |
|----|-----------|:------:|
| RF01 | Login + MFA + bloqueio + histórico | S1 (parcial) + S5 (TOTP) |
| RF02 | Recuperação de senha | S1 (força de senha) + S2 |
| RF03 | Perfis de acesso | S3 |
| RF04 | CRUD de usuários | S1 (modelo) + S2 |
| RF05 | Permissões granulares | S3 (módulo+ação; por-processo → contexto Processes) |
| RF06 | Logs de auditoria | S1 (acessos) + S5 |
| RF07 | SSO | Fora de escopo (fase posterior) |
| — | Planos e assinaturas (regras de negócio/landing) | S4 |
