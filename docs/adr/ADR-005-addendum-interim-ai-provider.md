# ADR-005 — Addendum (2026-09-30): interim AI provider is OpenRouter

Follows the same live-verification methodology as the `ADR-008` addendum (MinIO ->
`adobe/s3mock`) and `ADR-017` (supplier verification data sources): try a real candidate,
confirm it live against the actual service, then wire it into code -- not a documentation
exercise alone.

## Context

`ADR-005` calls for OpenAI + Anthropic adapters behind a single AI Gateway interface. At
the time EPIC-3 (Contract Intelligence) needed a working extraction pipeline, the project
had an OpenRouter API key already provisioned (free tier) but no real OpenAI or Anthropic
key yet. Blocking all of EPIC-3 on procuring a paid key was not necessary: OpenRouter
exposes an **OpenAI-compatible** chat completions API
(`https://openrouter.ai/api/v1/chat/completions`), so the "OpenAI adapter" ADR-005 already
calls for can be built against OpenRouter's base URL now and pointed at real OpenAI (or,
via a thin wrapper, Anthropic) later with **zero interface change** -- only configuration.

## Decision

Build the AI Gateway's OpenAI-compatible adapter (`app.ai_services.infrastructure.openrouter_gateway.OpenRouterAIGateway`)
against OpenRouter's endpoint, with two free-tier models selected as primary/fallback for
the AI-003 fallback chain:

- **Primary**: `nvidia/nemotron-3-super-120b-a12b:free` -- larger model, chosen for
  extraction quality.
- **Fallback**: `qwen/qwen3.8-27b:free` -- different vendor/model family, same general
  context window.

Both were verified live on 2026-09-29 against OpenRouter's `/api/v1/models` endpoint to
support the structured-output mechanism this pipeline requires
(`supported_parameters` including `response_format`/`structured_outputs`):

```
qwen/qwen3.8-27b:free           -> [..., "structured_outputs", ...]
nvidia/nemotron-3-super-120b-a12b:free -> [..., "response_format", "structured_outputs", ...]
```

Re-confirmed again on 2026-09-30, immediately before this addendum was written, same result.

### Config knobs (never hardcoded)

Added to `Settings` (`app/core/config.py`):

| Field | Default | Purpose |
|---|---|---|
| `ai_gateway_base_url` | `https://openrouter.ai/api/v1` | The OpenAI-compatible base URL -- pointing this at `https://api.openai.com/v1` (or an Anthropic-compatible proxy) later is the entire migration. |
| `openrouter_api_key` | `None`, from `OPENROUTER_API_KEY` env var | Never a code constant; already gitignored in `backend/.env`. |
| `ai_extraction_primary_model` | `nvidia/nemotron-3-super-120b-a12b:free` | Swappable per environment. |
| `ai_extraction_fallback_model` | `qwen/qwen3.8-27b:free` | Swappable per environment. |
| `ai_extraction_timeout_seconds` | `60.0` | Multi-page documents routinely exceed a short request timeout (`docs/04-architecture/components.md`'s own latency table). |
| `ai_extraction_max_input_chars` | `60,000` | Documented scope decision: whole-document truncation, not the structural chunking `document-intelligence.md` describes for very long contracts -- out of scope for this phase, logged rather than silently dropped. |
| `contract_extraction_confidence_threshold` | `0.82` | BR-CON-003's threshold -- see the dated addendum in `docs/05-ai/evaluation.md` for the full reasoning; cross-referenced from here because it's part of the same "interim AI setup" decision bundle. |

## The quota constraint (documented honestly)

OpenRouter's free tier is rate-limited at **50 requests/day per API key, account-wide**
(not per model) unless $10 in credits is added (raises it to 1000/day) -- confirmed live
via `GET /api/v1/credits` on 2026-09-29 and again on 2026-09-30 (`{"total_credits": 0,
"total_usage": 0}`, i.e. still on the free tier).

**This has a real implication for the AI-003 fallback design, stated plainly rather than
implied away**: the primary -> fallback model switch in `OpenRouterAIGateway.extract_contract`
protects against a *single model's own* errors, timeouts, or malformed/schema-invalid
output -- it does **not** protect against the account-wide daily quota being exhausted,
because a 429 from the quota gate hits every model on the same account identically. Both
failure modes surface through the same `AllProvidersExhaustedError` today; a caller cannot
currently distinguish "both models are individually broken" from "the account's 50
requests for today are gone." This is an accepted, documented limitation of the interim
setup, not a redundancy story dressed up as more robust than it is.

## Live verification performed

1. **Models-list check** (2026-09-29, re-confirmed 2026-09-30, no quota cost --
   `/api/v1/models` is not a chat-completion call): both models support
   `structured_outputs`/`response_format`, per the table above.
2. **One live end-to-end extraction call** (2026-09-30, spent deliberately and sparingly
   per this epic's budget): `OpenRouterAIGateway.extract_contract` called for real against
   a short synthetic contract snippet (an NDA-shaped paragraph naming a liability cap, a
   30-day termination notice, and a no-personal-data statement). Result: **HTTP 200, the
   primary model (`nvidia/nemotron-3-super-120b-a12b:free`) returned a JSON body that
   parsed and validated cleanly against `ModelExtractionOutput`** (this codebase's Pydantic
   transcription of `docs/05-ai/structured-extraction.md`'s schema) -- the plumbing (HTTP
   call, `response_format: json_schema` request, JSON parsing, schema validation,
   provenance-stamping) works end to end against the real API, not just against mocks.
   The model under-populated some structured fields (`contract_type`, `liability.type`
   came back `null`) while correctly identifying 4 clauses -- a prompt-quality/extraction-accuracy
   observation for `docs/05-ai/evaluation.md`'s golden-dataset work, not a plumbing defect;
   noted here for the record, not treated as this ADR's concern to fix.
3. **Test suite**: entirely hermetic per this epic's mandate -- every test in
   `tests/ai_services/` and `tests/contracts/` mocks the HTTP layer
   (`httpx.MockTransport`, mirroring `tests/suppliers/conftest.py`'s `mock_cnpj_registry`
   pattern) and makes zero real network calls. Only the one call in point 2 above hit the
   real API, run manually and once.

## Migration path to a real OpenAI/Anthropic key

Because the adapter is written against the OpenAI-compatible chat-completions shape:

- **Real OpenAI key**: set `ai_gateway_base_url=https://api.openai.com/v1`,
  `openrouter_api_key` (rename pending, or reuse the field) to the real OpenAI key, and
  `ai_extraction_primary_model`/`ai_extraction_fallback_model` to real OpenAI model names.
  Zero code change.
- **Real Anthropic key**: Anthropic's native API is not OpenAI-shaped, so this specific
  adapter would need either (a) Anthropic's own OpenAI-compatible-shim endpoint if/when
  available, or (b) a second adapter (`AnthropicAIGateway`) implementing the same
  `AIGatewayPort` Protocol (`app.ai_services.domain.ports`) -- exactly the "pluggable
  provider adapters" shape `ADR-005` already specifies. Either way, `Contracts & Documents`
  and every other caller are unaffected: they only ever depend on `AIGatewayPort` and
  `app.ai_services.application.extraction_service.get_ai_gateway()`'s factory, never a
  concrete adapter class.
- Raising the free-tier quota (add $10 credits -> 1000/day) requires no code change at
  all, only an OpenRouter account action.

## Consequences

- The fallback chain's real protection scope (single-model failure, not account-wide
  quota) must be kept in mind by anyone debugging a burst of
  `AllProvidersExhaustedError`s in production logs -- check the account's remaining daily
  quota (`GET /api/v1/credits`) before assuming both models are independently broken.
- `docs/05-ai/evaluation.md` carries its own dated addendum recording the interim
  `contract_extraction_confidence_threshold=0.82` value, cross-referenced from here.
- If OpenRouter's free tier changes terms again (as ADR-008's addendum found MinIO/LocalStack
  did), re-run this same live-verification methodology before switching, and update this
  addendum.
