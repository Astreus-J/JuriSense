# Agent Architecture

This document decides, per AI-touching process, whether JuriSense Gate uses a **deterministic
pipeline**, a **single tool-calling step**, or a **true multi-step (agentic) loop** — and states
explicitly why the default is not "build a multi-agent system."

## Guiding principle

The project owner's explicit instruction: **do not default to a multi-agent architecture because it
is trendy.** Multi-step agentic loops (planning, tool selection, iterative refinement, sub-agent
delegation) trade reliability and reproducibility for flexibility. JuriSense Gate's core value
proposition is the opposite of that trade-off: a customer's Legal/Compliance team needs to be able
to explain, months later, exactly why a given extraction or decision came out the way it did
(`ADR-010`, `docs/00-project/overview.md`'s "WHY, EVIDENCE, POLICY, SOURCE" promise). A pipeline that
runs the same deterministic sequence of steps for the same input is auditable and reproducible in a
way a multi-turn agent loop — where the model itself decides what to do next — is not.

The rule this document applies to every process: **use the least "agentic" pattern that gets the
task done correctly.** Reach for more agentic patterns only when the task is genuinely open-ended
(the number and kind of steps cannot be known in advance) and the cost of that unpredictability is
acceptable for the process in question.

## Decision framework

| Pattern | When it fits | Reliability/reproducibility | Cost/latency | Debuggability |
|---|---|---|---|---|
| **Deterministic pipeline** (fixed sequence of steps, at most one of which calls an LLM with a schema) | The steps and their order are known in advance; the LLM's job is narrow (extract/classify/summarize against a fixed schema) | High — same input, same step sequence, every time | Predictable, lowest | Highest — each step is independently testable and loggable |
| **Single tool-calling step** (one LLM call that may invoke 1 declared tool/function to fetch a fact before answering) | The task needs one piece of external context the prompt can't include directly, but doesn't need iterative reasoning | High — bounded to one tool round-trip | Low, slightly higher than pure pipeline | High — one call, one tool result, easy to log/replay |
| **True multi-step agent** (LLM plans, chooses among multiple tools, iterates until it decides it's done) | The task is genuinely open-ended: the right sequence of lookups/actions cannot be enumerated in advance and depends on intermediate findings | Lower — different runs can take different paths for the same input; requires strong guardrails (turn limits, tool allow-lists, human confirmation) to keep reproducible | Higher and variable — cost scales with how many turns the model decides to take | Lower — requires full trace logging (`observability.md`) to reconstruct what happened |

Reliability is weighted above flexibility for every process in this table unless a process is
explicitly marked otherwise below.

## Process-by-process decision (v1)

| Process | Pattern chosen | Rationale |
|---|---|---|
| **Contract structured extraction** | **Deterministic pipeline** | See "Contract extraction in detail" below — this is the highest-stakes AI process in the product and the one where reproducibility matters most. |
| **Contract type / risk classification** | **Deterministic pipeline** (a fixed classification call with an enumerated label set, no tool use) | A closed-label classification task never needs iteration; it's one schema-constrained call. |
| **Supplier data normalization assistance** | **Deterministic pipeline** | Mapping a `SupplierCheck`'s raw external-source payload into `SupplierProfile` fields is a fixed transformation, always followed by deterministic validation — no reasoning loop needed. |
| **Reviewer-facing summarization** | **Deterministic pipeline** | One call, fixed input (the extracted structured data + relevant clause text), fixed output shape (a short summary). No tool use needed. |
| **Precedent/context retrieval for a human reviewer** (`rag.md`) | **Single tool-calling step at most** (retrieval-then-present; the "tool" is the hybrid search query, and even that can be a plain deterministic retrieval call rather than an LLM-chosen one) | The retrieval query parameters (clause type, organization, top-k) are derived deterministically from the `RuleEvaluation`/`Clause` being reviewed — the LLM does not need to decide *whether* or *how* to search. |
| **(Future) Research Agent** — cross-referencing external regulatory/legal sources during a review | **True multi-step agent — explicitly deferred, see below** | This is the one capability in the current roadmap where the task shape (which sources to check, how many search-refine iterations are needed, when "enough" evidence has been gathered) is genuinely open-ended. |

## Contract extraction in detail (the reference pipeline)

```
1. Upload
     Document created (content_hash, storage_key) — docs/03-domain/domain-model.md
2. OCR / text extraction
     document-intelligence.md decides: native text layer vs. OCR route
3. Chunking (if needed for long contracts)
     document-intelligence.md chunking strategy
4. Single structured-extraction call
     One AI Gateway extract() call per contract (or per chunk set, merged deterministically),
     against the fixed JSON schema in structured-extraction.md — no follow-up calls, no
     model-driven branching
5. Provenance tagging
     Every extracted field's page/text_span/confidence is attached (part of the extract() contract,
     ADR-005) — not a separate reasoning step
6. Deterministic post-processing
     Schema validation (guardrails.md), currency/unit normalization, confidence-threshold check
     (BR-CON-003) — all plain code, not LLM calls
7. Persistence
     ContractVersion.extracted_data + Clause rows created; contract.analysis_completed emitted
```

This is **not** a multi-agent system: there is no step where the model decides which step to run
next, retries a different strategy on its own initiative, or delegates to another model/agent. Every
step is either a fixed deterministic transformation or exactly one schema-constrained LLM call. This
is a deliberate choice, for three concrete reasons specific to this product:

1. **Reproducibility is a product requirement, not a nice-to-have.** `ADR-010`'s aggregation model
   and the Decision Passport (`docs/03-domain/evidence.md`) only work if the same `ContractVersion`
   always yields the same `extracted_data` given the same model/prompt version — an agent that might
   take a different reasoning path on retry undermines that.
2. **Cost and latency predictability.** A pipeline with one Tier-2 extraction call has a bounded,
   estimable cost per contract (feeds directly into `ai-strategy.md`'s cost-control model); an agent
   loop's cost varies with how many turns it decides to take.
3. **Debuggability.** When an extraction is wrong, "which of these 7 fixed steps produced the wrong
   value" is answerable by inspecting one log per step (`observability.md`). "Why did the agent
   decide to take this particular path" is a much harder question to answer after the fact, and a
   much harder one to reproduce in a regression test (`evaluation.md`).

## Where a true agent loop is justified later (Phase 9+, not v1)

A **"Research Agent"** — one that, during a compliance review, autonomously searches and
cross-references external regulatory or legal sources (e.g., recent regulatory guidance relevant to
a clause type, case law/precedent beyond the organization's own historical decisions) — is a
plausible future capability that genuinely fits the "true multi-step agent" pattern, because:

- The right set of sources to check is not knowable in advance (it depends on what the contract
  contains and what the first search returns).
- It may need several search → read → refine-query iterations before it has enough to present.
- Its output is explicitly **supporting context for a human reviewer**, never an input to the
  deterministic Policy Engine (same boundary as `rag.md`'s precedent lookup) — so the lower
  reproducibility of an agent loop is acceptable here in a way it would not be for extraction.

This is explicitly scoped as a **Phase 9+ roadmap consideration** (`docs/09-planning/roadmap.md`),
**not a v1 capability**. If and when it is built, it must still respect the guardrails in
`guardrails.md` (bounded turn count, an explicit tool allow-list, no side-effecting actions without
human confirmation, and full step-by-step trace logging per `observability.md`) — an agent loop
being justified for this one process does not relax the "AI never decides the outcome" boundary,
which applies to the Research Agent's findings exactly as it applies to extraction output.

## Summary decision rule (for future processes not listed above)

When a new AI-touching process is proposed, answer these in order before choosing a pattern:

1. Can the sequence of steps be fully enumerated today, independent of what the AI returns at each
   step? → **Deterministic pipeline.**
2. Does it need exactly one piece of external context fetched before a single answer, with no
   iteration? → **Single tool-calling step.**
3. Does the task require the model to decide, based on intermediate results, what to do next, and is
   the output strictly advisory (never feeding the deterministic Policy Engine)? → **Multi-step
   agent**, built with explicit turn limits, tool allow-lists, and full trace logging.

If a process ever needs a multi-step agent **and** its output is meant to influence a
`RuleEvaluation`/`Decision`, that is a design error under the current architecture — normalize its
output into the evaluation context through `Policy & Compliance` exactly like any other AI output
(`ai-strategy.md`), never let the agent's own conclusion stand in for a rule outcome.
