# Structured Extraction Schema

This document specifies the exact JSON schema produced by the contract structured-extraction
`extract()` call (`ADR-005`), and how each field maps into the **normalized evaluation context** that
`docs/03-domain/policy-engine.md`'s rules consume. This schema is the concrete contract between
`AI Services` and `Contracts & Documents`/`Policy & Compliance` — it is what `AI-002`
(`docs/01-product/functional-requirements.md`) and `BR-CON-004`
(`docs/03-domain/business-rules.md`) mean in practice.

## Design rules for this schema

1. **Every leaf value carries provenance and confidence.** No field is a bare value — every
   extracted fact is wrapped as `{ "value": ..., "confidence": <0..1>, "provenance": { "document_id",
   "page", "text_span": { "start", "end" } } }`. This is a hard requirement (`ADR-005`), not a
   convenience — it is what `document-intelligence.md`'s `text_span` mechanism and `evaluation.md`'s
   citation-correctness check depend on.
2. **The schema is enforced via JSON schema / tool-calling, never freeform parsing** (`ADR-005`,
   `guardrails.md`). The AI Gateway rejects and retries a response that doesn't validate against this
   schema.
3. **Array items are wrapped individually** — each entry in `obligations`, `subprocessors`,
   `guarantees`, `penalties`, `deadlines` carries its own provenance/confidence, because different
   items in the same list often come from different pages/spans of the contract.
4. **`clauses[]` is a separate top-level array** from the field-level extraction above — it is the
   direct source for `Clause` rows (`docs/03-domain/domain-model.md`) and can include clause types
   that don't map to a single structured field (e.g. a broad "confidentiality" clause).

## Full schema (illustrative JSON Schema, informal draft)

```json
{
  "type": "object",
  "required": ["contract_version_id", "document_id", "extraction_run_id", "model", "extracted_at", "fields", "clauses"],
  "properties": {
    "contract_version_id": { "type": "string", "format": "uuid" },
    "document_id": { "type": "string", "format": "uuid" },
    "extraction_run_id": { "type": "string", "format": "uuid" },
    "model": {
      "type": "object",
      "required": ["provider", "model_name", "prompt_version"],
      "properties": {
        "provider": { "type": "string", "enum": ["openai", "anthropic"] },
        "model_name": { "type": "string" },
        "prompt_version": { "type": "string" }
      }
    },
    "extracted_at": { "type": "string", "format": "date-time" },
    "pagination_mode": { "type": "string", "enum": ["native", "synthetic"] },
    "fields": {
      "type": "object",
      "properties": {
        "contract_type": { "$ref": "#/$defs/extractedString" },
        "parties": {
          "$ref": "#/$defs/extractedValue",
          "description": "value is an array of { role, name, tax_id }"
        },
        "value": {
          "type": "object",
          "properties": {
            "amount": { "$ref": "#/$defs/extractedNumber" },
            "currency": { "$ref": "#/$defs/extractedString" }
          }
        },
        "duration": {
          "type": "object",
          "properties": {
            "start_date": { "$ref": "#/$defs/extractedDate" },
            "end_date": { "$ref": "#/$defs/extractedDate" },
            "auto_renewal": { "$ref": "#/$defs/extractedBoolean" }
          }
        },
        "termination": {
          "type": "object",
          "properties": {
            "notice_period_days": { "$ref": "#/$defs/extractedNumber" },
            "termination_for_convenience": { "$ref": "#/$defs/extractedBoolean" },
            "termination_for_cause_conditions": { "$ref": "#/$defs/extractedString" }
          }
        },
        "liability": {
          "type": "object",
          "properties": {
            "type": { "$ref": "#/$defs/extractedString", "description": "one of: capped | unlimited | mutual | not_specified" },
            "cap": { "$ref": "#/$defs/extractedNumber", "description": "cap amount, same currency as value.currency, null if type != capped" }
          }
        },
        "privacy": {
          "type": "object",
          "properties": {
            "processes_personal_data": { "$ref": "#/$defs/extractedBoolean" },
            "dpa_present": { "$ref": "#/$defs/extractedBoolean" }
          }
        },
        "obligations": { "type": "array", "items": { "$ref": "#/$defs/extractedString" } },
        "subprocessors": { "type": "array", "items": { "$ref": "#/$defs/extractedString" } },
        "jurisdiction": { "$ref": "#/$defs/extractedString" },
        "guarantees": { "type": "array", "items": { "$ref": "#/$defs/extractedString" } },
        "penalties": { "type": "array", "items": { "$ref": "#/$defs/extractedString" } },
        "deadlines": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "description": { "type": "string" },
              "date": { "$ref": "#/$defs/extractedDate" }
            }
          }
        }
      }
    },
    "clauses": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["clause_type", "page", "text_span", "confidence"],
        "properties": {
          "clause_type": { "type": "string" },
          "page": { "type": "integer" },
          "text_span": {
            "type": "object",
            "properties": { "start": { "type": "integer" }, "end": { "type": "integer" } }
          },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
          "text_excerpt": { "type": "string", "description": "short excerpt for reviewer UI display, not used for evaluation" }
        }
      }
    }
  },
  "$defs": {
    "provenance": {
      "type": "object",
      "required": ["document_id", "page", "text_span"],
      "properties": {
        "document_id": { "type": "string", "format": "uuid" },
        "page": { "type": "integer" },
        "text_span": {
          "type": "object",
          "properties": { "start": { "type": "integer" }, "end": { "type": "integer" } }
        }
      }
    },
    "extractedValue": {
      "type": "object",
      "required": ["value", "confidence", "provenance"],
      "properties": {
        "value": {},
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "provenance": { "$ref": "#/$defs/provenance" }
      }
    },
    "extractedString": { "allOf": [{ "$ref": "#/$defs/extractedValue" }], "properties": { "value": { "type": ["string", "null"] } } },
    "extractedNumber": { "allOf": [{ "$ref": "#/$defs/extractedValue" }], "properties": { "value": { "type": ["number", "null"] } } },
    "extractedBoolean": { "allOf": [{ "$ref": "#/$defs/extractedValue" }], "properties": { "value": { "type": ["boolean", "null"] } } },
    "extractedDate": { "allOf": [{ "$ref": "#/$defs/extractedValue" }], "properties": { "value": { "type": ["string", "null"], "format": "date" } } }
  }
}
```

## Worked example (populated instance)

```json
{
  "contract_version_id": "8f2e2f0e-1a2b-4c3d-9e4f-5a6b7c8d9e0f",
  "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "extraction_run_id": "d4c3b2a1-0f9e-8d7c-6b5a-4938271605f4",
  "model": { "provider": "anthropic", "model_name": "TBD", "prompt_version": "contract-extraction-v1" },
  "extracted_at": "2026-09-27T14:32:00Z",
  "pagination_mode": "native",
  "fields": {
    "contract_type": {
      "value": "saas_subscription",
      "confidence": 0.95,
      "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 1, "text_span": { "start": 0, "end": 240 } }
    },
    "parties": {
      "value": [
        { "role": "client", "name": "Acme Tecnologia Ltda.", "tax_id": "12.345.678/0001-90" },
        { "role": "supplier", "name": "CloudVendor S.A.", "tax_id": "98.765.432/0001-10" }
      ],
      "confidence": 0.93,
      "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 1, "text_span": { "start": 250, "end": 610 } }
    },
    "value": {
      "amount": {
        "value": 480000.00,
        "confidence": 0.97,
        "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 3, "text_span": { "start": 1200, "end": 1260 } }
      },
      "currency": {
        "value": "BRL",
        "confidence": 0.99,
        "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 3, "text_span": { "start": 1255, "end": 1258 } }
      }
    },
    "duration": {
      "start_date": { "value": "2026-10-01", "confidence": 0.96, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 2, "text_span": { "start": 800, "end": 820 } } },
      "end_date": { "value": "2027-09-30", "confidence": 0.96, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 2, "text_span": { "start": 825, "end": 845 } } },
      "auto_renewal": { "value": true, "confidence": 0.88, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 2, "text_span": { "start": 850, "end": 940 } } }
    },
    "termination": {
      "notice_period_days": { "value": 30, "confidence": 0.9, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 4, "text_span": { "start": 2100, "end": 2160 } } },
      "termination_for_convenience": { "value": true, "confidence": 0.85, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 4, "text_span": { "start": 2170, "end": 2260 } } },
      "termination_for_cause_conditions": { "value": "Material breach uncured for 15 days after written notice.", "confidence": 0.82, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 4, "text_span": { "start": 2270, "end": 2410 } } }
    },
    "liability": {
      "type": { "value": "unlimited", "confidence": 0.91, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 5, "text_span": { "start": 2900, "end": 3050 } } },
      "cap": { "value": null, "confidence": 0.91, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 5, "text_span": { "start": 2900, "end": 3050 } } }
    },
    "privacy": {
      "processes_personal_data": { "value": true, "confidence": 0.94, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 6, "text_span": { "start": 3400, "end": 3520 } } },
      "dpa_present": { "value": false, "confidence": 0.89, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 6, "text_span": { "start": 3400, "end": 3520 } } }
    },
    "obligations": [
      { "value": "Supplier shall maintain 99.9% uptime SLA.", "confidence": 0.87, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 3, "text_span": { "start": 1600, "end": 1660 } } }
    ],
    "subprocessors": [
      { "value": "AWS South America (São Paulo) region", "confidence": 0.8, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 6, "text_span": { "start": 3550, "end": 3610 } } }
    ],
    "jurisdiction": { "value": "São Paulo, Brazil", "confidence": 0.92, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 8, "text_span": { "start": 4800, "end": 4850 } } },
    "guarantees": [],
    "penalties": [
      { "value": "2% monthly penalty on late payment plus SELIC-indexed interest.", "confidence": 0.9, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 3, "text_span": { "start": 1700, "end": 1780 } } }
    ],
    "deadlines": [
      { "description": "First invoice due", "date": { "value": "2026-10-15", "confidence": 0.85, "provenance": { "document_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "page": 3, "text_span": { "start": 1800, "end": 1820 } } } }
    ]
  },
  "clauses": [
    { "clause_type": "liability", "page": 5, "text_span": { "start": 2900, "end": 3050 }, "confidence": 0.91, "text_excerpt": "Supplier's liability under this Agreement shall be unlimited with respect to..." },
    { "clause_type": "dpa", "page": 6, "text_span": { "start": 3400, "end": 3520 }, "confidence": 0.89, "text_excerpt": "Supplier processes personal data on behalf of Client. No separate Data Processing Agreement is attached." },
    { "clause_type": "termination", "page": 4, "text_span": { "start": 2170, "end": 2410 }, "confidence": 0.85, "text_excerpt": "Either party may terminate this Agreement for convenience upon 30 days' written notice..." }
  ]
}
```

## Mapping to the normalized evaluation context

`Policy & Compliance` builds the flat, typed **normalized evaluation context**
(`docs/03-domain/policy-engine.md` § Evaluation context) from this extraction output (plus supplier
evidence, out of scope here). This mapping is owned by `Policy & Compliance`'s application layer, not
`AI Services` — `AI Services` only ever produces the schema above (context boundary rule,
`ai-strategy.md`).

| `policy-engine.md` normalized field | Source in this schema |
|---|---|
| `contract.value.brl` | `fields.value.amount.value`, converted to BRL using `fields.value.currency.value` if not already BRL (conversion logic and rate source live in `Policy & Compliance`, not `AI Services`) |
| `contract.value.currency` | `fields.value.currency.value` |
| `contract.liability.type` | `fields.liability.type.value` |
| `contract.processes_personal_data` | `fields.privacy.processes_personal_data.value` |
| `contract.dpa_present` | `fields.privacy.dpa_present.value` |
| (clause-level evidence for a `RuleEvaluation`) | `clauses[]` entries, referenced by `clause_type`/`page`/`text_span` — this is how a rule like `LEGAL-008` ("Unlimited Liability Requires Legal Review") cites its supporting `Clause` |
| `supplier.sanctions_hit` | **Not from this schema** — sourced from `SupplierCheck`/`SupplierProfile` (`Suppliers` bounded context), included here only to clarify the evaluation context is not extraction-only |

Only fields whose `confidence` meets the minimum threshold (`BR-CON-003`, `evaluation.md`) are
allowed to populate the normalized context automatically; fields below threshold block
`ContractVersion.analyzed` until a human confirms them (`guardrails.md`) — the mapping above always
runs against the confirmed value, never a low-confidence raw extraction.
