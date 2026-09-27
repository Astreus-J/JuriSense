# ADR-014 — Deferred Payment Gateway Integration

## Status
Accepted (carried over from pre-pivot decision, formalized here)

## Context
Formalizes TR-003 from `docs/_legacy/tradeoffs.md`. Still applicable: JuriSense Gate's hackathon
cut and early customer validation do not require real billing to prove product value.

## Decision
Model `Plan`/`Subscription` with an explicit state machine (`trial`/`active`/`past_due`/
`cancelled`/`expired`) and enforce plan limits (suppliers analyzed, contracts reviewed, AI
executions — see `docs/02-business/pricing-strategy.md`), without integrating a real payment
gateway (Stripe or a Brazilian equivalent) in the first phases.

## Alternatives Considered
- **Integrate a gateway immediately**: real monetization sooner, but doubles scope and forces a
  premature commercial/legal decision on gateway choice before the product has paying-customer
  validation.

## Consequences
- Trial expiration has no automatic conversion path until a gateway is integrated (tracked as a
  post-hackathon roadmap item, `docs/09-planning/roadmap.md` Phase 10 — Enterprise).
- State machine states are designed from typical gateway webhook shapes so the eventual integration
  is additive, not a redesign.
