# ADR-004 — Policy Engine Expression Language

## Status
Accepted (spike completed 2026-09-30 — see "Spike findings" below; supersedes the "Proposed" status)

## Context
The Policy Engine is a core competitive component: organizations must be able to express rules like
"if the contract processes personal data and has no DPA, BLOCK" as data, not code, versioned, and
safely evaluated against untrusted-ish structured input (AI-extracted contract/supplier data).
Research (2026-09-27) compared four candidate technologies:

- **OPA (Rego)**: the most mature general-purpose policy engine (CNCF), dominant for
  infrastructure/API/Kubernetes authorization. Requires running Rego as a language most business
  users cannot read or author directly, and typically runs as a sidecar/service — operational
  overhead not justified for evaluating business rules over a few hundred contracts/suppliers.
- **AWS Cedar**: fast, schema-validated, purpose-built for **application authorization**
  (who-can-do-what-to-which-resource), not for expressing arbitrary business conditionals over
  extracted document data. AWS-specific tooling, thin ecosystem outside that use case.
- **CEL (Common Expression Language)**: a small, sandboxed, fast expression language designed
  exactly for "evaluate a boolean/typed expression against a data context inside your own process,"
  with official Python bindings (`cel-python`). No external service required.
- **JSONLogic**: even lighter, JSON-native rule expressions, trivial to store/version/diff, less
  expressive for complex boolean logic than CEL, but easier for a future no-code rule builder UI to
  generate safely.

## Decision
Adopt a **YAML rule authoring format** (`id`, `name`, `when`, `result`, `severity`, `approver_role`)
as the durable, versioned storage format for policies (see `docs/03-domain/policy-engine.md` for the
full schema and examples). The `when` clause compiles to a **CEL expression** evaluated in-process
against a normalized evidence context (supplier + contract + AI-extraction output). JSONLogic is
kept as the fallback/alternative compilation target specifically for rules authored through a future
visual/no-code rule builder, where JSONLogic's tree structure is easier to generate safely than raw
CEL text.

## Spike findings (EPIC-4 / STORY #55, live-verified 2026-09-30)

The spike built a working YAML-to-CEL compiler and rule-execution engine
(`app/policies/domain/rule_dsl.py`, `app/policies/application/evaluation_service.py`) against the
exact 5 worked-example rules in `docs/03-domain/policy-engine.md` (SANC-001, LGPD-001, LEGAL-008,
FIN-003, FIN-004), then wired it to real Supplier/Contract evidence end to end
(`tests/policies/test_simulation.py`). Answering the three questions this ADR's original Resolution
posed:

**1. `cel-python` packaging/performance.** `cel-python==0.5.0` installed cleanly via `uv add
cel-python` on this project's actual runtime (Python 3.14, though the project targets ">=3.13"),
pulling in `lark`, `google-re2`, `pendulum` as documented — no native/system dependency issues, no
build failures. Performance: a single pre-compiled CEL expression evaluates in ~230 microseconds
(measured: 2,000 calls to `Runner.evaluate()` against a pre-compiled program and a pre-converted
context, `celpy.json_to_cel()` itself costs ~25 microseconds separately). **Compiling** a CEL
expression from source (`Environment.compile()` + `Environment.program()`), by contrast, measured
~1.4 milliseconds per call when done fresh every time — over 1000x more expensive than evaluating an
already-compiled program. Consequence: `evaluation_service.py` caches every compiled program by its
exact CEL source string (`functools.lru_cache`, keyed on the expression text, safe because a
`Rule`'s compiled CEL strings are immutable for the lifetime of any single evaluation run and
identical strings are safe to share a cache entry across different rules). With caching, a full
5-rule policy evaluates against one context in low single-digit milliseconds total (each rule needs
two evaluations under the two-phase design below, so ~10 evaluate() calls, ~2.3ms) — not quite the
original "well under a millisecond for all 5 rules" framing from this ADR's Resolution, but still
negligible next to the request/DB I/O already present in any endpoint that would call it; packaging
and correctness, not raw speed, were the real risk, exactly as this ADR anticipated.

**2. Missing/null context fields.** Confirmed live: CEL raises `CELEvalError` by default on
undefined field access (`has(contract.value.brl)` guards a **genuinely absent** key correctly,
returning `False` with no error — but it does **not** guard a key that is *present with an explicit
JSON `null` value*: `has()` only tests structural presence, so `has(x)` is `True` even when `x` is
`null`, and the subsequent comparison then raises anyway). This directly matters for
`contract.value.brl` (null-able when a contract's currency isn't BRL, per `policy-engine.md`'s own
example fields) — the fix has two parts, both implemented:
  - The context builder (`app.policies.application.context_builder.normalize_context`, #60) never
    emits an explicit `null` leaf; an inapplicable field is **omitted from the context dict
    entirely**. This alone makes every `has()` guard behave correctly.
  - Because a single has()-guarded boolean expression can't distinguish "condition legitimately
    false" from "field missing" (both short-circuit `has(...) && ...` to `False`), and
    `RuleEvaluation.outcome` needs `NOT_APPLICABLE` distinguishable from `PASS` (ADR-010), the
    compiler (`rule_dsl.compile_rule_when`) produces **two** CEL expressions per rule — a
    `presence_cel` (an AND-chain of `has()` over every referenced path's prefixes) evaluated first,
    and a `condition_cel` (the actual comparison) evaluated only once presence is confirmed. This is
    the concrete two-phase evaluation `evaluation_service.evaluate_rule` runs, and it is the reason
    `RuleOutcome.NOT_APPLICABLE` is produced correctly and safely rather than silently defaulting to
    a wrong boolean.

**3. Hiding CEL from a policy author.** The YAML `when:` grammar (a flat mapping of
`dotted.path -> literal-or-{op: value}`, exactly as written in `policy-engine.md`'s 5 examples)
compiles cleanly to CEL without any author ever seeing CEL syntax. Implicit equality
(`processes_personal_data: true`), dotted-path field references (`contract.liability.type`), and the
`{gte: N}` comparison-operator shape all map directly onto CEL literals/operators
(`app.policies.domain.rule_dsl._cel_literal`/`_compile_condition_clause`). The one genuine grammar
decision this spike had to make itself: `policy-engine.md`'s own LGPD-001 example references
`processes_personal_data`/`dpa_present` **unprefixed**, even though the evaluation context exposes
them as `contract.processes_personal_data`/`contract.dpa_present` — the compiler resolves an
unprefixed key against the registered context-field registry (`app.policies.domain.context_schema`)
and accepts it only if it uniquely matches exactly one registered field, rejecting it as an unknown
field otherwise. All 5 worked examples, verbatim from the doc, parse and evaluate correctly under
this rule (`tests/policies/test_rule_dsl.py`).

**Rule conflict/priority handling** (the spike's third original question) turned out to need no
CEL/JSONLogic-specific answer at all: ADR-010's aggregation (`any BLOCK → BLOCK`, else `any REVIEW →
REVIEW` with highest-severity-wins approver routing) operates on the *already-evaluated* set of
`RuleOutcome`s, entirely downstream of which expression language ran each rule
(`evaluation_service.aggregate_preview`, tested against the tie-breaking case in
`tests/policies/test_evaluation_service.py`).

**Conclusion: CEL is accepted as the primary compilation target**, unchanged from this ADR's original
Decision. JSONLogic remains the documented fallback for a future no-code rule builder's output — not
implemented in this epic (no such builder exists yet to generate it), matching the original Decision
text.

## Alternatives Considered
See Context above (OPA, Cedar) — both rejected as wrong-fit, not "worse at everything."

## Consequences
- No new service to operate for v1 (CEL runs in-process); simpler ops story for the VPS deployment.
- Policy authors interact with YAML + a constrained `when` grammar, not raw CEL/JSONLogic — the
  authoring UI is responsible for hiding the compilation target.
- If OPA/Cedar-style fine-grained resource authorization is later needed (e.g., "who can view which
  specific supplier record"), that is a **separate** concern from this business-rule engine and
  should reuse the existing RBAC model (ADR-003), not this Policy Engine.
