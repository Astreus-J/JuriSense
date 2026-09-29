# ADR-017 — Supplier Verification Data Sources (Phase-2 Integration Spike)

## Status
Accepted

## Context
`docs/03-domain/supplier-compliance.md` ("Data sources") explicitly left the CNPJ registry and
CEIS/CNEP/CEPIM sanctions integration mechanism as `TBD`, pending "a Phase-2 integration spike."
EPIC-2 (Supplier Intelligence) needs a real `SupplierVerificationPort` implementation to satisfy
`SUP-002`/`SUP-003`/`SUP-004` — this ADR is the output of that spike: what was tried, what was
verified live, and what was chosen. It follows the same live-verification methodology used for the
ADR-008 addendum (MinIO → `adobe/s3mock`): try real candidates, confirm with an actual network call
or downloaded artifact, and only then wire the choice into code.

## Decision

### CNPJ registry
Use **BrasilAPI** (`https://brasilapi.com.br/api/cnpj/v1/{cnpj}`) as the `CnpjRegistryAdapter`'s
backend: free, no API key, no rate-limit gate encountered during the spike.

Verified live on 2026-09-28 with a real CNPJ (Banco do Brasil, `00000000000191`):
`curl https://brasilapi.com.br/api/cnpj/v1/00000000000191` → `HTTP 200` with a full registry
record (`descricao_situacao_cadastral`, `razao_social`, `natureza_juridica`, `data_inicio_atividade`,
`capital_social`, `cnae_fiscal_descricao`, `cnaes_secundarios`, `qsa` partner list, and address
fields `logradouro`/`numero`/`bairro`/`municipio`/`uf`/`cep`) — everything
`docs/03-domain/supplier-compliance.md`'s "Registry status" and "Corporate structure" categories
need. **ReceitaWS** (`https://receitaws.com.br/v1/cnpj/{cnpj}`) was verified live as a working
free alternative too (same CNPJ, `HTTP 200`, equivalent fields under different key names) and is
documented here as the fallback if BrasilAPI's free tier ever adds a gate, but BrasilAPI is chosen
as primary: it is community-run/open-source, documents its schema, and does not mask its uptime/
rate-limit terms behind a commercial tier the way ReceitaWS does.

One real, product-relevant limitation found during verification: BrasilAPI (mirroring the Receita
Federal source data itself) masks partner CPFs in `qsa` (e.g. `***550179**`), for LGPD reasons.
This means responsible-party sanctions matching (`docs/03-domain/supplier-compliance.md` §
"Responsible parties") cannot be done by exact CPF match from this source alone — the adapter
matches responsible parties to sanctions lists **by normalized name**, not by CPF, and this is a
documented best-effort limitation, not a silent gap (see `SanctionsAdapter` docstring and the
"Consequences" section below).

### Sanctions — CEIS / CNEP / CEPIM
**Portal da Transparência's live query API requires a registered API key**
(`chave-api-dados` header) — verified live on 2026-09-28:
`curl https://api.portaldatransparencia.gov.br/api-de-dados/ceis?pagina=1` → `HTTP 401`,
`{"Erro na API":"Chave de API não informada!..."}`. Per this spike's constraint, we do not
self-provision an external API key/credential, so the live per-call API is not an option here.

**The public bulk open-data extracts are real, current, and require no key.** Verified live on
2026-09-28 by downloading the actual files, not just checking a status code:

- `https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/ceis/20260928_CEIS.zip` →
  `HTTP 200`, a 3.4 MB zip containing `20260928_CEIS.csv` (~23,700 data rows), semicolon-delimited,
  `ISO-8859-1`-encoded, CRLF line endings, header row confirms the exact fields needed
  (`CPF OU CNPJ DO SANCIONADO`, `NOME DO SANCIONADO`, `RAZÃO SOCIAL`, `CATEGORIA DA SANÇÃO`,
  `DATA INÍCIO/FINAL SANÇÃO`, `ÓRGÃO SANCIONADOR`).
- `.../cnep/20260928_CNEP.zip` → `HTTP 200`, same shape.
- `.../cepim/20260928_CEPIM.zip` → `HTTP 403` (no file for that exact date) but
  `.../cepim/20260925_CEPIM.zip` → `HTTP 200` — CEPIM is real and downloadable the same way, just
  published on a sparser/irregular cadence than CEIS/CNEP (which appear to publish daily). This
  means the adapter/refresh job cannot assume "today's file always exists" and must search
  backward from today for the most recent available extract per dataset.

**Chosen approach: scheduled bulk-download + local indexing**, exactly matching
`supplier-compliance.md`'s documented fallback option, for the reason stated there: a batch
approach is the only way to get complete CEIS/CNEP/CEPIM coverage without a paid/registered API
key, and per-check download of a multi-MB CSV would make every `SupplierCheck` unacceptably slow
and would re-fetch the same day's data thousands of times.

- A Celery task (`app.integrations.infrastructure.tasks.refresh_sanctions_index`) downloads the
  most recent available extract for each of CEIS/CNEP/CEPIM (searching backward from today, per
  the irregular-cadence finding above), parses it, and replaces that list's rows in the
  `sanctions_entries` table (one logical table, `list_name` column distinguishing CEIS/CNEP/CEPIM).
  This is the same "replace, don't accumulate stale duplicates" idea as `SupplierProfile`, applied
  to a reference dataset instead of a per-supplier one.
- `SanctionsAdapter` (the concrete adapter behind `SupplierVerificationPort`'s sanctions leg) never
  makes a live network call per check — it queries `sanctions_entries` by normalized document
  (CNPJ/CPF, digits only) and by normalized responsible-party name.
- If `sanctions_entries` has never been refreshed for a given list (no rows / no
  `refreshed_at` yet in an environment), the sanctions source reports
  `source_status: unavailable` — and because sanctions is a **mandatory** source
  (`supplier-compliance.md` step 3), the whole `SupplierCheck` fails rather than completing as if
  clean. Populating the index for the first time in a given environment (running the Celery task
  once) is an operational/day-2 step, not something this ADR or its code silently works around —
  this mirrors `BR-SUP-004`'s "never silently look clean" requirement one level up, into the
  reference-data layer itself.

## Alternatives Considered
- **Live Portal da Transparência API for CEIS/CNEP/CEPIM**: rejected for now — requires a
  self-registered API key, which is an external credential outside this spike's scope to
  provision. Revisit once the product has a real account/key management process; the
  `SanctionsAdapter`'s `SupplierVerificationPort`-facing contract does not change if the backend
  later moves from local-index to live-API, so this is not a dead end.
- **ReceitaWS as the CNPJ registry primary**: viable, verified live, kept as documented fallback
  (see above) rather than primary, for the reasons given.
- **Per-check live scrape of Portal da Transparência's public search UI**: rejected — fragile
  (HTML-shape-dependent, not a stable contract), and likely against the site's terms for
  programmatic per-request use at check-time volume; the official bulk-data channel is the
  intended machine-readable path for exactly this use case.
- **Deterministic fixture data (the "no real integration works" fallback)**: not needed — both the
  CNPJ registry and the sanctions bulk extracts were verified live and working; fixtures are used
  only in the hermetic test suite (mocked HTTP transport / mocked repository), never as a
  production code path.

## Consequences
- One more scheduled job to operate (`refresh_sanctions_index`, run periodically — exact cadence
  is a follow-up decision, tracked alongside the still-`TBD` re-check cadence in
  `supplier-compliance.md`; daily is a reasonable starting default given CEIS/CNEP's observed
  daily publish cadence), alongside the CNPJ registry's already-adopted "no local job" live-call
  model.
- Responsible-party sanctions matching is name-based, not CPF-based, because of the CPF-masking
  finding above — a known, documented precision limitation (false negatives are more likely than
  false positives for common names), not a silent gap. Tightening this (e.g. via a paid registry
  API that returns unmasked CPFs) is future-backlog work, not blocking for Phase 2.
- `sanctions_entries` is intentionally a global (not per-organization) reference table — sanctions
  lists are public, jurisdiction-wide facts, not tenant data; only `SupplierCheck`/`SupplierProfile`
  rows (which reference it) are tenant-scoped.
- If any of these free sources stop being freely reachable in the future, re-run this same
  live-verification methodology (real HTTP call / real file download, not just documentation
  reading) before switching, and update this ADR — exactly as ADR-008's addendum instructs for the
  storage layer.
