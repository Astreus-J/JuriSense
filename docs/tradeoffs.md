# Registro de Decisões (Tradeoffs)

Decisões de arquitetura e escopo que tinham alternativas reais, registradas na fase de planejamento. Formato: o que foi decidido, alternativas pesadas e o que foi sacrificado.

---

## TR-001 — JWT stateless com refresh rotativo (vs. sessões server-side)

- **Fase:** plano (Accounts, 2026-07-07)
- **Decisão:** access token JWT curto (15min) + refresh token rotativo (7d), blocklist de revogação em Redis.
- **Alternativas:** sessões opacas em Redis (revogação trivial, mas todo request consulta o Redis); JWT de longa duração sem refresh (simples, mas revogação impossível).
- **Sacrifício:** revogação imediata de access tokens não é garantida na janela de 15min; complexidade da rotação de refresh.

## TR-002 — RBAC como dados (tabelas) e não como enum em código

- **Fase:** plano (Sprint 3)
- **Decisão:** permissões perfil→módulo→ação persistidas em tabela, com seeds dos 5 perfis do README; admin customiza (RF03).
- **Alternativas:** papéis fixos hardcoded (mais simples, mas RF03 exige customização); ABAC/policy engine (Casbin/OPA) — poder que ainda não precisamos.
- **Sacrifício:** consulta de permissão vira acesso a dado (mitigado com cache); migração futura para permissão por-processo (RF05 completo) exigirá extensão do modelo.

## TR-003 — Planos/assinaturas sem gateway de pagamento na fase 1

- **Fase:** plano (Sprint 4)
- **Decisão:** modelar `Plano`/`Assinatura` com máquina de estados (trial/ativa/inadimplente/cancelada/expirada) e enforcement de limites, sem cobrança real.
- **Alternativas:** integrar Stripe/PagSeguro já na Sprint 4 (valor imediato, mas dobra o escopo e trava em decisão comercial de gateway).
- **Sacrifício:** trial expira sem caminho de conversão automática até o gateway entrar; estados desenhados "no escuro" a partir de webhooks típicos.

## TR-004 — Multi-tenancy lógico por organizacao_id (vs. schema por tenant)

- **Fase:** plano (Accounts)
- **Decisão:** todas as tabelas de tenant carregam `organizacao_id`; isolamento garantido nos repositórios; teste de acesso cruzado obrigatório nas auditorias.
- **Alternativas:** schema PostgreSQL por tenant (isolamento forte, migrações e conexões complexas em um SaaS com muitos escritórios pequenos); RLS do Postgres (defesa extra, custo de setup — candidata a evolução).
- **Sacrifício:** um bug de filtro é vazamento entre tenants — por isso o item fixo de tenant-bypass na auditoria de toda sprint.

## TR-005 — Auditoria de segurança como gate de fim de sprint

- **Fase:** plano (processo)
- **Decisão:** toda sprint termina com auditoria (skills `security-review` + `insecure-defaults` + checklist manual); achados críticos/altos bloqueiam a sprint seguinte.
- **Alternativas:** auditoria única no fim do projeto (mais barata, mas achados chegam tarde e caros); análise contínua em CI apenas (não cobre lógica de negócio como escalada de privilégio).
- **Sacrifício:** ~3 pontos de capacidade por sprint dedicados a auditoria em vez de features.
