# Legal & Compliance Posture

This document defines JuriSense Gate's own legal positioning — distinct from the compliance
decisions the *product* generates for customers. It exists because `docs/01-product/product-definition.md`
and `docs/01-product/non-functional-requirements.md` both need a single, authoritative place to
point to for "what does JuriSense claim, and not claim, about its own outputs."

## Core positioning

JuriSense Gate is **decision support software**, not a law firm, not a substitute for a customer's
own legal counsel, and not a source of legal advice. Every `Decision` it produces
(`docs/03-domain/domain-model.md`) is the output of (a) AI-assisted extraction, explicitly
provenance-tagged and never treated as ground truth without the extraction-confidence gating
already defined in `docs/03-domain/business-rules.md` (`BR-CON-003`), and (b) deterministic policy
rules that the *customer's own organization* authored and published
(`docs/03-domain/policy-engine.md`). JuriSense does not assert that a `BLOCK` or `APPROVE` outcome
is legally correct in an absolute sense — it asserts that the outcome is what the customer's own
configured policy says, given the evidence collected, and that the evidence trail is
reproducible and auditable (`docs/03-domain/evidence.md`).

## Where this posture must be reflected

- **Terms of Service / customer contract**: an explicit clause stating JuriSense Gate provides
  compliance workflow automation and decision support, not legal advice, and that the customer
  remains responsible for its own legal and regulatory compliance obligations.
- **In-product disclosure**: a visible, persistent notice on every `Decision` view stating the same,
  so a reviewer never mistakes an automated `APPROVE` for a legal sign-off.
- **Sales and marketing materials**: consistent language avoiding "certifies," "guarantees," or
  "legally clears" — the product's own vocabulary (per `docs/00-project/glossary.md`) is
  `APPROVE`/`REVIEW`/`BLOCK` against a *policy*, not against "the law" in the abstract.

## Status: TBD

- **Current preferred option**: the positioning above (decision support, not legal advice; customer
  retains ultimate compliance responsibility; policy-relative rather than law-relative outcomes).
- **Why undecided**: the exact disclaimer language (contractual and in-product) needs review by
  outside counsel qualified in Brazilian consumer/B2B contract law and, once international
  jurisdiction packs are live, in each additional jurisdiction's equivalent — this is a legal
  drafting task, not a product/engineering one, and this documentation pass should not fabricate
  binding legal text.
- **Resolution**: commission outside counsel review before the product's first paid contract is
  signed (tracked as a `Phase 1` / `Phase 10` — Enterprise gating item in
  `docs/09-planning/roadmap.md` and `docs/09-planning/risks.md`).
- **Decision artifact**: this file will be updated in place with the reviewed language once
  available; no new ADR is needed since this is a legal/commercial artifact, not an architecture
  decision.

## Relationship to LGPD and data protection

JuriSense Gate itself is a data controller/processor for the documents and personal data customers
upload to it, independent of the compliance decisions it renders about *their* suppliers. Its own
LGPD posture (data processing agreement with customers, sub-processor list, data residency,
retention) is covered operationally in `docs/06-blockchain/privacy.md` (for the anchoring-specific
privacy boundary) and `docs/07-engineering/security.md` (for security/encryption practice), and
commercially in a customer-facing DPA — also gated on the same outside-counsel review above.
