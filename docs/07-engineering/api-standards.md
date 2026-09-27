# API Standards

REST conventions for every HTTP endpoint exposed by the backend, across all 8 bounded contexts.
These conventions are new (the existing `Accounts` routes predate this document and are
grandfathered under the migration note below); every new endpoint from any context follows them.

## Versioning strategy

- All routes are mounted under **`/api/v1/...`**. The existing `Accounts`/`Users` routers are
  currently mounted at `/api/...` with no version segment (`app/api/router.py`,
  `api_router = APIRouter(prefix="/api")`); adding the `v1` segment for those routers is tracked
  migration work (`docs/09-planning/pivot-migration.md`), not silently done as a side effect of
  unrelated changes — a version bump on live routes needs its own coordinated change (client update,
  redirect/deprecation window).
- A breaking change to a resource's shape or semantics ships as `/api/v2/<resource>` alongside the
  still-serving `/api/v1/<resource>`, not as an in-place breaking edit. "Breaking" means: a field is
  removed or renamed, a field's type changes, a previously-optional field becomes required, or a
  status code for an existing case changes.
- Additive changes (a new optional field, a new endpoint, a new enum value in a non-exhaustively-matched
  field) do **not** require a version bump.
- `/api/docs` (Swagger UI) and `/api/openapi.json` continue to serve the live schema for whichever
  versions are mounted — FastAPI's built-in OpenAPI generation is the source of truth for the
  contract; no hand-maintained API reference document duplicates it.

## Resource naming & HTTP semantics

- Resource paths are plural nouns: `/suppliers`, `/contracts`, `/policies`, `/compliance/reviews`,
  `/approvals`, `/decisions`, `/evidence`.
- Standard verbs: `POST /resource` create, `GET /resource/{id}` read one, `GET /resource` list,
  `PATCH /resource/{id}` partial update (matches the existing `UpdateUserRequest` pattern — only
  fields present in the body are changed), `DELETE /resource/{id}` only where the domain model
  actually allows deletion (most compliance entities are append-only/soft-deleted per
  `docs/03-domain/domain-model.md` and never hard-deleted through the API).
- Sub-resource actions that are not pure CRUD are modeled as a `POST` to a verb-suffixed path, not
  a repurposed `PATCH`: `POST /suppliers/{id}/reviews`, `POST /compliance/check`,
  `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`, `POST /decisions/{id}/override`.

## Pagination

- List endpoints use **cursor-based pagination**, not offset/limit, because compliance data
  (decisions, audit events, evidence) is append-only and grows monotonically — offset pagination
  drifts under concurrent inserts.
- Query parameters: `limit` (default 20, max 100) and `cursor` (opaque, base64-encoded, returned by
  the previous page — never a raw row id the client should interpret).
- Response envelope for every list endpoint:

```json
{
  "items": [ ... ],
  "next_cursor": "eyJpZCI6ICI2M2..." ,
  "has_more": true
}
```

- Filtering/sorting parameters are resource-specific and documented per endpoint in its OpenAPI
  description (docstring), not in this cross-cutting document.

## Standardized error response shape

Every error response — across every context — uses one shape, matching FastAPI's native
`HTTPException` detail mechanism but with a structured `detail`, not a bare string, for anything
beyond the simplest cases:

```json
{
  "detail": {
    "code": "SUPPLIER_NOT_FOUND",
    "message": "Supplier not found.",
    "request_id": "req_01hz3k9m2p8f7q1n6t4x0v5c3d"
  }
}
```

- `code` is a stable, machine-readable, `UPPER_SNAKE_CASE` string, unique per distinct error
  condition, safe for a client to branch on (unlike `message`, which may be reworded).
- `message` is a human-readable, English, client-safe string — never a stack trace, an internal
  exception's `str()`, or a SQL error.
- `request_id` echoes the request-id-propagation value (see below) so a support conversation or bug
  report can be tied directly to server-side logs.
- Validation errors (`422`) additionally include a `fields` array
  (`[{"field": "contract.value.brl", "message": "must be a positive number"}]`), reusing FastAPI's
  Pydantic validation output reshaped into this envelope rather than FastAPI's raw default shape.
- This is a superset of, not a replacement for, the domain-error-to-HTTP-status mapping in
  `docs/07-engineering/coding-standards.md`'s error handling section — that section says *which*
  status code; this section says what the *body* looks like.

## Idempotency for mutating endpoints

Decision/approval actions are exactly the kind of endpoint where a retried request (client timeout,
double-click, a proxy retry) must not double-apply:

- Every mutating endpoint that has an external or hard-to-reverse effect — `POST /suppliers/{id}/reviews`,
  `POST /contracts`, `POST /compliance/check`, `POST /approvals/{id}/approve`,
  `POST /approvals/{id}/reject`, `POST /decisions/{id}/override` — accepts an optional
  `Idempotency-Key` request header (a client-generated UUID).
- The server stores `(organization_id, endpoint, idempotency_key) → response` for 24 hours (Redis,
  matching the TTL pattern already used for token stores). A repeated request with the same key
  within that window returns the **original** stored response (same status code and body) without
  re-executing the action.
- Without an `Idempotency-Key` header, the endpoint executes normally every time — idempotency is
  opt-in from the client's perspective but the server-side mechanism is mandatory infrastructure for
  the listed endpoints, consistent with the append-only, never-double-fire nature of decisions
  (`ADR-010`, `docs/03-domain/domain-model.md` `Decision` invariants).
- `POST /decisions/{id}/override` in particular must never apply twice — a duplicated override with
  two different justifications recorded would corrupt the audit trail's meaning of "why was this
  approved."

## Request ID propagation

- Every inbound request is assigned a `request_id` (accepted from an `X-Request-ID` header if the
  caller supplies one — e.g. the frontend or an upstream Nginx — otherwise generated server-side as
  a ULID).
- The `request_id` is: echoed back in every response (`X-Request-ID` header), included in the
  standardized error body (above), attached to every structured log line emitted while handling that
  request (`docs/07-engineering/observability.md`), and passed through to any Celery task enqueued as
  part of handling the request, so an async AI-extraction job's logs can be traced back to the HTTP
  request that triggered it.
- Implemented as FastAPI middleware in `app/core/observability.py`, applied once at the app level —
  no per-context router needs to handle this itself.

## OpenAPI / docs generation

- FastAPI's built-in OpenAPI generation is used as-is — already exposed at `/api/docs` (Swagger UI)
  and `/api/openapi.json` (`app/main.py`). No separate hand-maintained API reference.
- Every Pydantic request/response schema gets a `Field(description=...)` for non-obvious fields (an
  enum whose values aren't self-explanatory, a field with a unit like `contract.value.brl`) — this is
  the same "docstring for non-obvious WHY" policy from `coding-standards.md`, applied to schema
  fields because it becomes visible, useful documentation in `/api/docs` for free.
- Routers are tagged by bounded context (`tags=["suppliers"]`, `tags=["compliance"]`, etc.), matching
  the existing `tags=["auth"]` pattern, so `/api/docs` groups endpoints the same way the codebase is
  organized.

## Example endpoint surface (per the product's mission)

These sketches show how the conventions above apply to the mission's suggested API surface. They are
illustrative of shape and status codes, not a full schema reference (that lives in each context's
`api/schemas.py` and is generated into `/api/openapi.json`).

### `POST /api/v1/suppliers`
Creates a `Supplier` (Suppliers context). `201 Created` with the created resource;
`409 Conflict` (`code: SUPPLIER_ALREADY_EXISTS`) if `tax_id` + `organization_id` already exists
(`BR-SUP-002`). Requires `procurement` or `admin` role-module-action grant on `suppliers:create`.

### `POST /api/v1/suppliers/{id}/reviews`
Triggers a new `SupplierCheck` against external sources (CEIS/CNEP/CEPIM for the Brazil pack).
`202 Accepted` — the check runs asynchronously via Celery (ADR-006); response body includes the
`SupplierCheck.id` a client polls or receives via webhook/notification. Idempotency-Key supported.

### `POST /api/v1/contracts`
Creates a `Contract` and its first `ContractVersion` from an uploaded `Document`. `201 Created`;
kicks off async AI extraction (`contract.version_created` event). Enforces malware-scanned upload
validation (`docs/07-engineering/security.md`) before accepting the file.

### `POST /api/v1/compliance/check`
Runs a `ComplianceReview` for a given `contract_version_id` against the organization's current
`PolicyVersion`. `202 Accepted` (evaluation may involve async AI-dependent evidence gathering) with
a `ComplianceReview.id`; or `200 OK` with the completed review inline if evaluation is fast enough
to complete synchronously (implementation detail, not a contract change — the response always
includes `status` so a client doesn't need to guess which path was taken). Idempotency-Key required
in practice given this triggers billable AI usage.

### `GET /api/v1/decisions/{id}`
Returns the full `Decision` — status, `valid_until`, `supersedes_decision_id`, and links to its
`ComplianceReview`'s `RuleEvaluation`s and its `EvidencePackage`. `404` if not found or cross-tenant
(never `403`, per the no-enumeration rule). Requires read access to the `approvals`/`compliance_reviews`
module for the caller's organization.

### `GET /api/v1/evidence/{id}`
Returns one `EvidencePackage`'s manifest (its `Evidence` list and `merkle_root`), and its
`BlockchainAnchor` status if anchored. Authenticated, tenant-scoped.

### `GET /verify/{hash}` (note: not under `/api/v1`)
The **public, unauthenticated** verification endpoint (`docs/06-blockchain/verification.md`) — given
an evidence hash (or a short verification code), returns whether it matches an anchored
`EvidencePackage` and the anchor's on-chain proof, with **no** organization-internal data (no
contract content, no supplier PII) in the response. Because it is public, it is the one endpoint
called out explicitly in `docs/07-engineering/security.md` for mandatory rate limiting — it lives
outside `/api/v1` deliberately, as a distinct, minimal, low-trust surface rather than another
resource under the authenticated API, and it is not versioned the same way (a stable hash-in →
proof-out contract is expected to be a long-lived public URL, e.g. shared on a signed contract's
cover page).
