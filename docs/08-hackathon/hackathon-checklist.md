# Checklist do Hackathon — Status vs. Requisitos

> Data do levantamento: **13/10/2026**. **Atualização 14/10/2026 (confirmado pelo usuário): o
> prazo real de submissão é 31/10/2026**, não 05/11 como assumido no resto deste documento —
> faltam 17 dias a partir de hoje (14/10), não 23. Toda a seção "Ordem sugerida de ataque" abaixo
> precisa ser comprimida de acordo; as datas de semana ali ainda não foram reajustadas.
> Método: cada item foi conferido contra o repositório real (código, migrations, CI, docs), e não
> apenas contra os docs de planejamento. Referências: `hackathon-requirements.md`,
> `fallback-mvp.md`, `submission-plan.md`, `demo-scenario.md`, `pitch.md`, `hackathon-strategy.md`.
>
> **Limites desta auditoria**: a suíte de testes **não foi executada** (o `uv` não está instalado
> no shell usado). Portanto "feito" significa "implementado no código com testes presentes", e não
> "testes verificados como verdes hoje". A rubrica oficial do DoraHacks continua desconhecida (ver
> `hackathon-requirements.md` §2), então os critérios abaixo são os **inferidos**.
>
> **Atualização 15/10/2026**: desta vez a suíte de testes **foi executada de verdade** contra a
> stack real (`docker compose up`, não mock), não só lida no código — ver
> `docs/07-engineering/performance-baseline.md`. Isso achou e corrigiu 4 bugs reais que
> silenciosamente ameaçavam o demo inteiro (detalhe na seção "Riscos" abaixo). Também:
> `gitleaks` rodado de novo manualmente (histórico completo, 128 commits) a pedido do usuário —
> `no leaks found`, confirmando o item de segurança da 4.11. E a infraestrutura de banco/storage
> mudou: Postgres e MinIO agora são self-hosted (não mais Neon/Cloudflare R2) — ver os addenda de
> 2026-10-15 em `ADR-001`/`ADR-008`; isso não muda nenhum item funcional desta checklist, é uma
> decisão de hosting, não um recurso do produto.
>
> **Atualização 15/10/2026 (continuação)**: dois itens fecharam nesta mesma sessão, depois do
> levantamento acima. (a) `ANCHORING_PROVIDER` foi de fato alternado para
> `constellation_digital_evidence` (não mais `transparency_log`) e verificado ao vivo: uma
> submissão real de âncora chamou `POST /fingerprints` da Constellation (200) e um `GET` seguinte
> confirmou `status: FINALIZED_COMMITMENT` com hashes reais de snapshot — ver o addendum de
> 2026-10-15 na `ADR-007`. Isso fecha o risco "credencial obtida mas não alternada" (ver "Riscos a
> acompanhar" abaixo); fica a ressalva de que é config de runtime, não fato permanente — reconfirmar
> antes do demo/submissão. (b) Um pitch deck (4.2) chegou a ser montado nesta sessão — um deck de
> 12 slides em `docs/08-hackathon/pitch-deck/` mais uma cópia idêntica como Claude Artifact — mas
> foi descartado por decisão do usuário em 16/10/2026 (não será usado); ambos os dois removidos. O
> item volta a "a fazer".

Legenda: ✅ feito · 🟡 parcial / precisa de verificação · ⬜ a fazer

## Placar

| Área | ✅ | 🟡 | ⬜ | Total |
|---|---|---|---|---|
| 1. Pipeline do Hackathon Cut (engenharia) | 12 | 0 | 0 | 12 |
| 2. Tecnologia de patrocinador e blockchain | 4 | 1 | 1 | 6 |
| 3. Prontidão do demo | 0 | 1 | 5 | 6 |
| 4. Materiais de submissão | 1 | 4 | 6 | 11 |
| **Total** | **17** | **6** | **12** | **35** |

**Leitura**: o *produto* está essencialmente completo (área 1), e a trilha de blockchain também
está praticamente fechada (área 2 — só falta publicar o transparency log remoto, 2.6, e reconfirmar
o "Verify" ao vivo contra um anchor Constellation real, 2.4). O que falta agora é quase todo
*empacotamento do demo* (área 3) e os materiais de submissão restantes, incluindo o pitch deck de
novo (4.2 — o que foi montado em 15/10 foi descartado). Nada do que resta é engenharia difícil, mas
tudo tem data-limite.

---

## 1. Pipeline do Hackathon Cut (engenharia)

Corresponde aos itens 1–10 do `fallback-mvp.md`. Os "pisos não cortáveis" desse documento estão
indicados.

- [x] **1.1 Organizações, identidade, RBAC e multi-tenancy** — `backend/app/identity/`, já em
  inglês, RBAC como dado, lockout e convites. (item 1)
- [x] **1.2 Fornecedor + verificação de CNPJ/sanções** — `suppliers/` e `integrations/`
  (`cnpj_adapter.py`, `sanctions_source.py` para as bases CEIS/CNEP/CEPIM, ADR-017). Adaptadores
  reais, então o fallback "demo mode" não é necessário. (item 2)
- [x] **1.3 Upload de contrato + hash SHA-256 + scanner** — `contracts/`; o
  `document_scanner.py` aceita PDF, DOCX e TXT com checagem de falsificação de tipo. (item 3)
- [x] **1.4 Extração estruturada por IA com proveniência** — o schema de `ai_services/` inclui
  responsabilidade e `dpa_present`; gate de confiança e confirmação humana em `contracts/`. (item 4)
  *Ressalva*: o gateway roda em modelos gratuitos do OpenRouter (addendum da ADR-005); ver 3.5.
- [x] **1.5 Policy Engine** — DSL YAML → CEL, versões imutáveis, simulação e exceções; a regra
  `LGPD-001` está ligada ao schema de contexto e à DSL. (item 5, "as regras executam de verdade")
- [x] **1.6 Agregação de compliance (ADR-010)** — `policies/application/compliance_review_service.py`
  e `evaluation_service.py`. (item 6, "qualquer BLOCK vence")
- [x] **1.7 Máquina de estados de aprovações** — baseada em banco, varredura de SLA via Celery
  Beat, guarda de override, limite de retentativas e reavaliação com `supersedes_decision_id`.
  (item 7)
- [x] **1.8 Decision Passport** — read-model com execução de IA, versões de política, fontes
  externas e revisores (`evidence/application/decision_passport_service.py`) + tela no frontend.
  (item 8)
- [x] **1.9 EvidencePackage + raiz Merkle** — raiz recomputável e triggers append-only no banco.
- [x] **1.10 Interface `AnchoringProvider` + adaptadores** — adaptador Constellation DED e
  adaptador de transparency log atrás da mesma interface (ADR-007, aceita). (item 9)
- [x] **1.11 Página pública de verificação** — `frontend/src/app/verify/page.tsx` +
  `evidence/api/public_routes.py`, com rate limit. (item 10)
- [x] **1.12 Telas do frontend para o fluxo inteiro** — fornecedores, contratos, políticas,
  compliance, aprovações, decisões, evidências, integrações e configurações.

## 2. Tecnologia de patrocinador e honestidade sobre blockchain

- [x] **2.1 Spike da ADR-007 concluído e documentado** — Constellation testada primeiro; o
  bloqueio foi encontrado e registrado (credenciais, não o SDK).
- [x] **2.2 O fallback aparece rotulado na interface** — o `VerificationResultCard.tsx` exibe o
  `transparency_log` como fallback rotulado, nunca como blockchain (risks.md, risco 4).
- [x] **2.3 Apenas hashes são ancorados** — garantido por desenho em `anchoring_service`, ADR-007
  e docs de privacidade. *Não foi reauditado de forma independente nesta passada.*
- [ ] **2.4 🟡 O "Verify" faz chamada real ao provedor** — a submissão de âncora já chama a
  Constellation de verdade desde 2.5 (confirmado via `POST`/`GET` diretos contra a API real). O que
  falta: exercitar o próprio fluxo de `verification_service.py` / página pública `/verify` contra um
  anchor Constellation real — isso ainda não foi reconfirmado nesta sessão, só a chamada direta à
  API fora da rota da aplicação.
- [x] **2.5 Credenciais da Constellation DED** — **obtidas, testadas ao vivo, e o provedor já está
  ativo**. As 4 credenciais (`CONSTELLATION_DED_API_KEY/ORG_ID/TENANT_ID/PRIVATE_KEY`) chegaram e
  foram testadas em 2026-10-12. Em 2026-10-15, `ANCHORING_PROVIDER` foi de fato alternado de
  `transparency_log` para `constellation_digital_evidence` (os 10 testes que dependiam do default
  antigo foram ajustados para fixar o provider explicitamente — `Settings(anchoring_provider=...)`
  num teste, um `monkeypatch` autouse no `conftest.py` de evidence — em vez de herdar do `.env`
  compartilhado), e a troca foi verificada ao vivo: uma `Decision` real disparou `POST
  /fingerprints` (200) e um `GET` seguinte retornou `status: FINALIZED_COMMITMENT` com
  `batchGlobalSnapshotHash`/`batchMetagraphSnapshotHash` reais — ver o addendum de 2026-10-15 na
  `ADR-007`. **Importante**: isso é um valor de configuração de runtime, não um fato permanente —
  reconfirmar qual provedor está ativo antes do demo/submissão final, exatamente como a própria ADR
  pede.
- [ ] **2.6 Publicar o transparency log em um remoto público** — o módulo faz commits locais e,
  de propósito, nunca faz push. Enquanto isso não for feito, a alegação "público e verificável por
  terceiros" não vale de ponta a ponta para o fallback. Exige autorização explícita (ação
  voltada ao exterior).

## 3. Prontidão do demo (`demo-scenario.md`)

- [ ] **3.1 Script de seed do tenant do demo** — "Acme Tecnologia Ltda.", um admin, um aprovador
  com papel `legal` e um `PolicyVersion` publicado com `LGPD-001`, `LEGAL-008`, `FIN-003`
  (idealmente `FIN-004` e `SANC-001`). Não existe script de seed em `backend/` nem em `scripts/`.
- [ ] **3.2 Contratos de exemplo do demo** — dois PDFs da "CloudDocs Software Ltda.": v1
  (R$ 480.000/ano, 24 meses, renovação automática, responsabilidade ilimitada, dados pessoais, sem
  DPA) e v2 (DPA incluído, responsabilidade limitada). Nenhum encontrado no repositório.
- [ ] **3.3 Ensaio completo ponta a ponta** — rodar os 23 passos do `demo-scenario.md` como um
  apresentador faria, no mínimo duas vezes. Esperado: v1 → BLOCK, v2 → REVIEW → Legal aprova →
  Passport → âncora → verify. Pelo repositório, ainda não foi feito.
- [ ] **3.4 Âncora pré-submetida** — enviar a âncora minutos antes de apresentar; só o `verify`
  é ao vivo (notas do apresentador em `demo-scenario.md`).
- [ ] **3.5 Provedor de IA confiável para o demo** — modelos gratuitos do OpenRouter podem sofrer
  rate limit ou mudar. Providenciar uma chave paga da OpenAI/Anthropic (ADR-005) ou, no mínimo,
  testar os modelos gratuitos no dia anterior à gravação.
- [ ] **3.6 🟡 Ambiente publicado** — VPS + Docker Compose conforme `deployment.md`, acessível
  durante toda a janela de julgamento (05/11 a 05/12). Progresso em 15/10: `docker-compose.prod.yml`
  agora existe (builds de produção, Postgres+MinIO self-hosted sem porta publicada), mas só
  validado como config YAML — nunca rodado contra uma VPS real, e ainda falta o proxy
  reverso/TLS (Nginx) antes do backend/frontend pararem de publicar porta direto. O vídeo
  gravado continua o fallback aceito.

## 4. Materiais de submissão (`submission-plan.md` §1)

- [x] **4.1 Roteiro do pitch** — `pitch.md` (problema / solução / por que agora / por que nós /
  pedido / frase final).
- [ ] **4.2 Pitch deck (8–12 slides)** — montar a partir do `pitch.md`. Uma primeira versão (12
  slides, `docs/08-hackathon/pitch-deck/` + uma cópia como Claude Artifact) foi montada em 15/10/2026
  e **descartada por decisão do usuário em 16/10/2026** (não será usada; ambas as cópias removidas).
  Precisa ser refeito do zero antes da submissão.
- [ ] **4.3 Vídeo de demo (3–5 min assumidos)** — não iniciado; planejado para 02–03/11.
- [ ] **4.4 🟡 Repositório público no GitHub** — o remoto existe (`Astreus-J/JuriSense`); a
  visibilidade não foi verificada. Decidir o que expor antes de torná-lo público (ver 4.11).
- [ ] **4.5 🟡 `README.md` raiz** — aponta para `docs/08-hackathon/`, mas a seção "Project
  status" está desatualizada (ainda diz que os novos bounded contexts são "a fase atual"). O
  `CLAUDE.md` está desatualizado da mesma forma.
- [ ] **4.6 🟡 Write-up técnico da integração blockchain para a submissão** — a base existe em
  `docs/06-blockchain/` (845 linhas) e na ADR-007; falta a versão voltada ao juiz: interface,
  adaptador escolhido e por quê, o que é ancorado, como um terceiro verifica, e a declaração
  direta de que ICP e Story Protocol foram avaliados e não forçados.
- [ ] **4.7 Dados do time** — nomes, papéis e contato.
- [ ] **4.8 Conteúdo da página BUIDL / projeto** — depende de 4.9 para saber os campos exatos.
- [ ] **4.9 🟡 Checagem manual de `dorahacks.io/hackathon/legal-hack-2026`** — trilhas, rubrica de
  julgamento, formato da submissão. **Prazo confirmado pelo usuário em 2026-10-14: 31/10/2026**
  (não 05/11 como o resto deste documento assumia — ver nota no topo do arquivo). Ainda faltam:
  rubrica de julgamento e lista exata de bounties por patrocinador (ICP/Constellation/Story) —
  nenhuma fonte de terceiros checada (CompeteHub) trouxe isso; a página oficial continua
  bloqueando fetch automático (405).
- [ ] **4.10 Segunda checagem no DoraHacks** (plano: Semana 5, 25–31/10).
- [ ] **4.11 Limpeza antes de publicar** — antes de abrir o repositório: confirmar que não há
  segredos (o gitleaks roda no CI, com allowlist da chave Fernet de desenvolvimento), decidir se
  `docs/_legacy/` e `docs/auditorias/` permanecem, e corrigir a descrição em português que sobrou
  no `backend/pyproject.toml` e os comentários em `backend/app/main.py`.

---

## Ordem sugerida de ataque

1. **Hoje**: 4.9 (ler a página do DoraHacks) — 2.5 já está feito.
2. **Esta semana (13–17/10)**: 3.1 e 3.2 (seed e contratos de exemplo), 3.5 (chave de IA) e a
   primeira execução de 3.3.
3. **Semana de 18–24/10**: corrigir o que o ensaio quebrar; iniciar 3.6 (deploy); 4.5 (README).
4. **Semana de 25–31/10**: 2.5 e 2.6 para fechar o caminho real da âncora; 4.6 (write-up);
   4.2 (deck); 4.10 (nova checagem).
5. **01–05/11**: feature freeze, novos ensaios de 3.3, 3.4, 4.3 (vídeo), 4.7, 4.8 e submissão
   em 04–05/11 (não na última hora).

## Riscos a acompanhar

- ~~Credencial da Constellation obtida, mas `ANCHORING_PROVIDER` ainda não foi alternado para
  ela~~ → **fechado em 15/10/2026**: provedor trocado e verificado ao vivo (ver 2.5). Risco
  residual, menor: como é valor de config (não fato permanente), reconfirmar que ele continua ativo
  logo antes do demo/submissão — se tiver revertido para `transparency_log` por qualquer motivo,
  dizer isso em voz alta no pitch em vez de deixar qualquer material de submissão (deck, write-up)
  afirmar algo desatualizado.
- **Instabilidade da IA gratuita durante a gravação** → 3.5.
- **Rubrica ou formato desconhecidos** → 4.9 agora, e não na Semana 6.

### Risco fechado em 15/10/2026: teste de carga achou 4 bugs reais que quebrariam o demo em silêncio

Rodar a stack real sob carga (não a suíte mockada) achou e corrigiu, no mesmo dia:
1. **A âncora blockchain inteira estava quebrada** — faltava o binário `git` na imagem Docker do
   celery-worker, então **toda** `Decision` falhava ao tentar ancorar (`evidence.submit_anchor`),
   silenciosamente, em background. Isso é exatamente o passo final do roteiro do demo (3.3/3.4) e
   da verificação pública (2.4/item 10) — sem esse fix, o demo chegaria até "Decision Passport" e
   a âncora nunca apareceria, sem nenhum erro visível na hora.
2. O worker do Celery nunca processava extração de contrato de verdade em produção (ficava
   tentando pra sempre) — achado só rodando o processo real, invisível nos testes.
3. O índice de sanções ficava vazio por até 24h após qualquer restart — toda verificação de
   fornecedor falharia nesse intervalo (sanções é fonte obrigatória).
4. Uma corrida de requisições concorrentes em `/compliance/reviews` retornava um 500 cru em vez
   de um 409 limpo.

Todos os 4 corrigidos e verificados ao vivo (não só testados) no mesmo dia — ver
`docs/07-engineering/performance-baseline.md`. Mitigação adicional recomendada antes do ensaio da
3.3: depois de rodar o `docker compose up` do ambiente de demo, confirmar nos logs do
celery-worker que `evidence.submit_anchor` realmente sucede, não só que a review/decision foi
criada.
