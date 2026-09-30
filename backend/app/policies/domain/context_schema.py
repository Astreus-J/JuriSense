"""The normalized evaluation-context schema (#60, docs/03-domain/policy-engine.md
"Evaluation context & input normalization", docs/04-architecture/components.md rule 3).

This is the single source of truth for every dotted field path a `Rule.when` clause may
reference, and the shape `app.policies.application.context_builder.normalize_context`
must produce. Keeping both sides (`rule_dsl`'s unknown-field validation and the
normalizer) pointed at one registry means a rule can never reference a path the
normalizer doesn't know how to populate, or vice versa.

## Design decisions (#60)

- **Only scalar leaves are exposed.** `SupplierProfile.responsible_parties`/
  `corporate_structure`/`address` and `ContractFields.obligations`/`subprocessors`/
  `guarantees`/`penalties`/`deadlines` are list/dict-shaped evidentiary detail a human
  reviewer reads, not something a `{gte: N}`/equality rule condition reasons about --
  `SupplierProfile`'s own docstring already states this design intent ("everything else
  here is contextual/evidentiary detail Policy & Compliance never parses directly").
  Only scalar (bool/str/int/float) leaves are in this registry.
- **Every extracted-field leaf surfaces only its `.value`.** Per `ContractFields`
  (`app.ai_services.domain.schema`), each leaf is `{value, confidence, provenance}` --
  rules reason about facts, not AI confidence/provenance (BR-CMP-001: rules evaluate
  *normalized evidence*, never raw AI output).
- **`contract.processes_personal_data`/`contract.dpa_present` flatten out the
  `privacy.` nesting level** `ContractFields.privacy` uses internally, matching
  `policy-engine.md`'s LGPD-001 example verbatim (it references these two fields
  unprefixed even by `contract.` -- see `rule_dsl.resolve_path`'s bare-name fallback).
- **`contract.value.brl` is currency-normalized, not FX-converted.** No FX-conversion
  requirement exists anywhere in the docs. If `contract.value.currency == "BRL"`,
  `contract.value.brl` is set to `contract.value.amount`; otherwise the key is *omitted
  entirely* from the context (never set to `null`) so a rule referencing it evaluates to
  `NOT_APPLICABLE` rather than crashing or silently comparing against a sentinel (see
  `rule_dsl`'s has()-guarded two-phase presence/condition compilation for why "omitted"
  and "explicit null" are not interchangeable for CEL's `has()` macro).
"""

# Every valid dotted path a Rule's `when` clause may reference, organized by namespace.
# `resolve_path` in `rule_dsl.py` validates every `when` key against this set (directly,
# or via the documented bare-name shorthand for an unambiguous leaf name).

SUPPLIER_CONTEXT_PATHS: frozenset[str] = frozenset(
    {
        "supplier.registry_status",
        "supplier.sanctions_hit",
        "supplier.activity_mismatch",
        "supplier.address_flag",
        "supplier.cnae_code",
    }
)

CONTRACT_CONTEXT_PATHS: frozenset[str] = frozenset(
    {
        "contract.contract_type",
        "contract.value.amount",
        "contract.value.currency",
        "contract.value.brl",
        "contract.duration.start_date",
        "contract.duration.end_date",
        "contract.duration.auto_renewal",
        "contract.termination.notice_period_days",
        "contract.termination.termination_for_convenience",
        "contract.liability.type",
        "contract.liability.cap",
        "contract.processes_personal_data",
        "contract.dpa_present",
        "contract.jurisdiction",
    }
)

ALL_CONTEXT_PATHS: frozenset[str] = SUPPLIER_CONTEXT_PATHS | CONTRACT_CONTEXT_PATHS
