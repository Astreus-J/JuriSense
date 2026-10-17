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
>
> **Atualização 16/10/2026**: o usuário enviou prints da página real
> `dorahacks.io/hackathon/legal-hack-2026`, resolvendo boa parte do item 4.9 de uma vez — ver
> `hackathon-requirements.md` §1 para os fatos completos. **Achado crítico**: os bounties ao vivo
> desta edição são **Chainlink** ("Best workflow with CRE") e **RYO-CHAN** ("Autonomous Agents") —
> **não** ICP/Constellation/Story Protocol como a pesquisa original (bloqueada por 405/403) tinha
> assumido. Isso inverte a premissa central da `ADR-007`. **Decisão do usuário (16/10/2026): manter
> Constellation DED como provider**, sem perseguir o bounty do Chainlink — ver o addendum de
> 16/10/2026 na `ADR-007` para o racional completo. Também nesta atualização: 4.4 (repo público),
> 4.7 (dados do time) e 4.8 (config da página BUIDL) foram marcados como prontos por instrução
> direta do usuário (serão/foram resolvidos direto na plataforma, não no repositório), e o write-up
> técnico (4.6) foi escrito — `docs/06-blockchain/submission-writeup.md`.

Legenda: ✅ feito · 🟡 parcial / precisa de verificação · ⬜ a fazer

## Placar

| Área | ✅ | 🟡 | ⬜ | Total |
|---|---|---|---|---|
| 1. Pipeline do Hackathon Cut (engenharia) | 12 | 0 | 0 | 12 |
| 2. Tecnologia de patrocinador e blockchain | 5 | 1 | 0 | 6 |
| 3. Prontidão do demo | 3 | 1 | 2 | 6 |
| 4. Materiais de submissão | 6 | 3 | 2 | 11 |
| **Total** | **26** | **5** | **4** | **35** |

**Leitura**: o *produto* está essencialmente completo (área 1), a trilha de blockchain praticamente
fechada (área 2 — só falta reconfirmar o "Verify" ao vivo, 2.4), e materiais de submissão (área 4)
muito avançados (repo, write-up, dados do time, BUIDL e limpeza resolvidos ou tomados como prontos —
só falta o README raiz, a segunda checagem do DoraHacks, e o pitch deck, que precisa ser refeito). A
prontidão do demo (área 3) também avançou bastante: seed e contratos de exemplo prontos e
verificados contra a stack real, decisão tomada de manter OpenRouter gratuito. **O que resta agora é
essencialmente o ensaio ponta a ponta (3.3) e o vídeo** (roteiro pronto, gravação em andamento).
Restam só 4 itens genuinamente "a fazer". Data real: 31/10, 22:01 — cerca de 2 semanas.

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
- [x] **2.6 Publicar o transparency log em um remoto público** — **já estava feito**, a checklist
  é que estava desatualizada: o push aconteceu em 15/10/2026, com autorização explícita (Plane
  #207) — `repo_path` (histórico git, `entries.jsonl`, `PUBLIC_KEY.txt`) foi enviado para
  `https://github.com/Astreus-J/jurisense-transparency-log` (público, clonável anonimamente,
  "verified live" no momento do push; ver o docstring de `transparency_log_provider.py` e o commit
  `e86c043`). **Não é automático**: se novas âncoras forem criadas sob `transparency_log` depois do
  push, o espelho público fica defasado até um novo `git push` manual. Em 16/10/2026 o usuário
  decidiu que **não precisa republicar agora** — como a Constellation é o provider ativo desde
  15/10, não deveria haver âncoras novas sob `transparency_log` para publicar mesmo. Reavaliar só se
  o fallback for ativado de fato (ex.: Constellation cair) antes da submissão/demo.

## 3. Prontidão do demo (`demo-scenario.md`)

- [x] **3.1 Script de seed do tenant do demo** — `backend/scripts/seed_demo.py` (novo, 16/10/2026):
  cria "Acme Tecnologia Ltda." (plano Business), um admin, um aprovador com papel `legal`, e publica
  uma `PolicyVersion` com `LGPD-001`, `LEGAL-008`, `FIN-003`, `SANC-001`. **Rodado e verificado
  contra a stack real** (`docker compose exec backend uv run python scripts/seed_demo.py`) —
  idempotente, confirmado que uma segunda execução não duplica nada. `FIN-004` foi deliberadamente
  deixado de fora: seu `approver_role` documentado é `director`, que **não existe** em
  `app.identity.domain.constants.Role` (achado neste levantamento) — uma REVIEW dessa regra não
  teria para quem rotear. Isso é uma lacuna real do domínio, não um bug do script; registrado aqui
  em vez de inventar um papel só para o demo.
- [x] **3.2 Contratos de exemplo do demo** — `docs/08-hackathon/demo-assets/contracts/` (novo,
  16/10/2026): `clouddocs-saas-v1-original.pdf` (R$480.000/ano, 24 meses, renovação automática,
  responsabilidade ilimitada, dados pessoais, sem DPA) e `clouddocs-saas-v2-corrigido.pdf` (DPA via
  cláusula LGPD completa, responsabilidade limitada a 12 meses de mensalidade). Em português
  (conteúdo voltado ao cliente fictício, permitido pela regra de idioma do `CLAUDE.md`), com
  cláusulas numeradas para citação pela extração de IA. Gerados com `reportlab`
  (`uv run --with reportlab`, sem adicionar dependência ao backend) e verificados visualmente via
  `pdftoppm`.
- [ ] **3.3 Ensaio completo ponta a ponta** — rodar os 23 passos do `demo-scenario.md` como um
  apresentador faria, no mínimo duas vezes. Com 3.1/3.2 prontos, desbloqueado; ainda não executado.
- [ ] **3.4 Âncora pré-submetida** — enviar a âncora minutos antes de apresentar; só o `verify`
  é ao vivo (notas do apresentador em `demo-scenario.md`).
- [x] **3.5 Provedor de IA confiável para o demo** — decisão do usuário (16/10/2026): continuar
  usando os modelos gratuitos do OpenRouter, sem trocar para uma chave paga. Risco residual mantido
  (ver "Riscos a acompanhar"): testar os modelos gratuitos no dia anterior à gravação continua
  recomendado, já que não foi trocado o provedor, só aceito o risco.
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
- [ ] **4.3 🟡 Vídeo de demo (3–5 min assumidos)** — roteiro de narração completo escrito
  (`docs/08-hackathon/demo-video-script.md`, novo, 16/10/2026: narração palavra por palavra +
  marcações de ação para os 23 passos do `demo-scenario.md`, ~4,5 min no ritmo natural de leitura).
  A gravação em si está em andamento na mesma sessão: Playwright (via `npx`, Chromium já em cache)
  para capturar a tela de verdade navegando pelo app real, `espeak-ng` para a narração sintetizada
  (voz robótica, não natural — ver nota de limitação abaixo) e `ffmpeg` para legenda embutida.
- [x] **4.4 Repositório público no GitHub** — tomado como feito por instrução direta do usuário
  (16/10/2026). *Não reverificado nesta sessão*: a visibilidade real do remoto `Astreus-J/JuriSense`
  e a limpeza da 4.11 (segredos, `docs/_legacy/`, comentários em português) continuam como pré-
  requisitos de fato antes de abrir o repo, mesmo com o item marcado pronto aqui.
- [ ] **4.5 🟡 `README.md` raiz** — aponta para `docs/08-hackathon/`, mas a seção "Project
  status" está desatualizada (ainda diz que os novos bounded contexts são "a fase atual"). O
  `CLAUDE.md` está desatualizado da mesma forma.
- [x] **4.6 Write-up técnico da integração blockchain para a submissão** —
  `docs/06-blockchain/submission-writeup.md` (novo, 16/10/2026): interface `AnchoringProvider`,
  adaptador escolhido (Constellation DED) e por quê, o que é ancorado, como um terceiro verifica, e
  uma seção honesta sobre o achado de 16/10 — os bounties ao vivo são Chainlink/RYO-CHAN, não
  ICP/Constellation/Story como se assumia; o documento não afirma mais que "ICP e Story foram
  avaliados e não forçados" (isso deixou de ser a narrativa relevante), e sim que a abstração
  `AnchoringProvider` foi desenhada para não depender de acertar a lista de patrocinadores.
- [x] **4.7 Dados do time** — tomado como pronto por instrução direta do usuário (16/10/2026): será
  preenchido direto na página do DoraHacks, não é um artefato do repositório.
- [x] **4.8 Conteúdo da página BUIDL / projeto** — tomado como pronto por instrução direta do
  usuário (16/10/2026): configuração feita direto na plataforma.
- [ ] **4.9 🟡 Checagem manual de `dorahacks.io/hackathon/legal-hack-2026`** — avançou bastante em
  16/10/2026: o usuário enviou prints da página real, confirmando prazo exato (31/10 22:01), prize
  pool ($20.000), tags, tecnologia de plataforma (Bitcoin/Ethereum) e — o achado mais importante —
  os bounties reais (Chainlink, RYO-CHAN; não ICP/Constellation/Story). Fatos completos em
  `hackathon-requirements.md` §1. Ainda faltam: rubrica de julgamento detalhada e o conteúdo da aba
  "Tracks" (não capturada nos prints enviados). O usuário disse que vai mandar mais prints.
- [ ] **4.10 Segunda checagem no DoraHacks** (plano: Semana 5, 25–31/10) — parcialmente antecipada
  pelos prints de 16/10 acima; ainda vale uma passada final perto da submissão.
- [x] **4.11 🟡 Limpeza antes de publicar** — feito nesta sessão (16/10/2026):
  - **Segredos**: `gitleaks` instalado (`go install github.com/zricethezav/gitleaks/v8@latest`,
    não estava no ambiente) e rodado de duas formas. `gitleaks git` (histórico completo, 136
    commits — 8 a mais que a última checagem de 15/10): **no leaks found**. `gitleaks dir`
    (diretório de trabalho inteiro, incluindo arquivos ignorados pelo git) encontrou 21 ocorrências,
    todas em `frontend/.next/` (artefatos de build do Next.js) e `project-management/plane/.env` —
    **confirmado que ambos estão no `.gitignore` e nunca foram commitados** (`git log --all
    --full-history` vazio para o `.env`). Falso alarme, não vazamento real.
  - **Texto em português corrigido**: `backend/pyproject.toml`'s `description` (estava em
    português E descrevia o produto antigo pré-pivot — corrigido para inglês e para o produto
    atual) e os dois comentários em `backend/app/main.py`.
  - **`docs/_legacy/` e `docs/auditorias/` — ainda é uma decisão sua, não tomei por conta própria**:
    inspecionei os dois. `docs/auditorias/` são auditorias de segurança reais (0 Critical/0 High,
    achados Medium todos corrigidos na mesma passada) — tecnicamente isso é um ponto a favor na
    narrativa de "rigor/auditabilidade", não um risco. `docs/_legacy/` é a documentação completa do
    produto pré-pivot (ERP jurídico "SCHEMAJUD") com seu próprio README explicando o pivô — não hÃ¡
    segredo ali, só a pergunta de narrativa "mostrar um pivô abandonado passa confiança ou
    desconfiança a um jurado". Minha recomendação: manter — é transparência, e o próprio
    `docs/09-planning/pivot-migration.md` já trata isso como registro histórico esperado. Mas a
    palavra final é sua.

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
- **Rubrica ou formato desconhecidos** → 4.9 agora, e não na Semana 6; rubrica detalhada e aba
  "Tracks" ainda não confirmadas mesmo depois dos prints de 16/10.
- **Bounty real não é Constellation (novo, 16/10/2026)** → os únicos bounties ao vivo são Chainlink
  e RYO-CHAN; nenhum deles é Constellation/ICP/Story. Decisão do usuário: manter Constellation DED
  mesmo assim (ver addendum de 16/10 na `ADR-007`), então este risco não é "corrigir o código", é
  **narrativo**: todo material de submissão (pitch, write-up, resposta a pergunta de jurado) precisa
  parar de alegar "Constellation é patrocinador confirmado desta edição" como fato atual — isso já
  foi corrigido no write-up novo (4.6) e na `ADR-007`, mas qualquer pitch deck futuro (4.2, a ser
  refeito) precisa nascer já com essa correção, não repetir o erro do deck descartado.

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
