# ADR-011 — JWT Stateless Auth with Rotating Refresh Tokens

## Status
Accepted (carried over from pre-pivot decision, formalized here)

## Context
Formalizes the decision originally recorded as TR-001 in `docs/_legacy/tradeoffs.md` (2026-07-07),
made during the `Accounts` bounded context build. It remains valid: `Accounts` is reused as the
`Identity & Organizations` context in the new product (`ADR-003`), and its auth mechanism is
domain-agnostic.

## Decision
Short-lived JWT access tokens (15 min) plus a rotating refresh token (7 days), with a Redis-backed
revocation blocklist for refresh token jtis.

## Alternatives Considered
- **Opaque server-side sessions in Redis**: trivial revocation, but every request pays a Redis
  round-trip.
- **Long-lived JWT with no refresh**: simplest, but revocation becomes impossible before expiry.

## Consequences
- Immediate access-token revocation is not guaranteed within the 15-minute window (accepted
  trade-off); refresh rotation adds implementation complexity already paid for and tested.
- No changes needed for the pivot — this mechanism is identity-domain-agnostic.
