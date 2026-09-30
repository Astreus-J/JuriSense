"""The normalized evaluation-context builder (#60; docs/03-domain/policy-engine.md
"Evaluation context & input normalization"; docs/04-architecture/components.md rule 3).

`normalize_context` is a **pure function**: given a `SupplierEvidenceDTO`/
`ContractEvidenceDTO` (or `None` for either, when no supplier/contract is in scope), it
deterministically returns the same nested context dict every time, with no database
access, no clock reads, and no other hidden state -- see `tests/policies/
test_context_builder.py` for the property test asserting this. `build_context_for_contract_version`
is the thin, side-effecting wrapper that fetches the DTOs through the two evidence ports
and hands them to the pure function; nothing else in this module touches a database.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.application.evidence_service import (
    get_normalized_terms,
    get_supplier_id_for_contract_version,
)
from app.contracts.domain.evidence import ContractEvidenceDTO
from app.suppliers.application.evidence_service import get_normalized_profile
from app.suppliers.domain.evidence import SupplierEvidenceDTO

_BRL_CURRENCY_CODES = frozenset({"BRL"})


def _prune_nulls(node: dict[str, Any]) -> dict[str, Any]:
    """Recursively drops any key whose value is `None` (or, after pruning, an empty
    dict), and any key whose value is itself a dict with nothing left in it. This is the
    concrete mechanism behind "an inapplicable field is omitted, never set to null" (see
    `app.policies.domain.context_schema`'s docstring) -- CEL's `has()` macro only
    correctly treats a *missing* key as NOT_APPLICABLE-safe, not an explicit `null` one
    (see `app.policies.domain.rule_dsl`'s module docstring for the live-verified reason).
    """
    pruned: dict[str, Any] = {}
    for key, value in node.items():
        if value is None:
            continue
        if isinstance(value, dict):
            nested = _prune_nulls(value)
            if nested:
                pruned[key] = nested
            continue
        pruned[key] = value
    return pruned


def _supplier_context(supplier: SupplierEvidenceDTO | None) -> dict[str, Any]:
    if supplier is None:
        return {}
    return _prune_nulls(
        {
            "registry_status": supplier.registry_status,
            "sanctions_hit": supplier.sanctions_hit,
            "activity_mismatch": supplier.activity_mismatch,
            "address_flag": supplier.address_flag,
            "cnae_code": supplier.cnae_code,
        }
    )


def _contract_value_brl(contract: ContractEvidenceDTO) -> float | None:
    """`contract.value.brl`: currency-normalized, not FX-converted (#60's scope call --
    no FX-conversion requirement exists anywhere in the docs). `None` here means "not
    applicable" (a non-BRL contract, or no value extracted at all), which `_prune_nulls`
    then omits from the context entirely -- a `{gte: N}` rule on `contract.value.brl`
    correctly evaluates to NOT_APPLICABLE for a non-BRL contract, never a wrong `False`."""
    if contract.value_amount is None or contract.value_currency is None:
        return None
    if contract.value_currency.strip().upper() not in _BRL_CURRENCY_CODES:
        return None
    return contract.value_amount


def _contract_context(contract: ContractEvidenceDTO | None) -> dict[str, Any]:
    if contract is None:
        return {}
    return _prune_nulls(
        {
            "contract_type": contract.contract_type,
            "value": {
                "amount": contract.value_amount,
                "currency": contract.value_currency,
                "brl": _contract_value_brl(contract),
            },
            "duration": {
                "start_date": contract.duration_start_date,
                "end_date": contract.duration_end_date,
                "auto_renewal": contract.duration_auto_renewal,
            },
            "termination": {
                "notice_period_days": contract.termination_notice_period_days,
                "termination_for_convenience": contract.termination_for_convenience,
            },
            "liability": {
                "type": contract.liability_type,
                "cap": contract.liability_cap,
            },
            # Flattened out of ContractFields' `privacy.*` nesting -- matches
            # policy-engine.md's LGPD-001 example exactly (see context_schema.py).
            "processes_personal_data": contract.processes_personal_data,
            "dpa_present": contract.dpa_present,
            "jurisdiction": contract.jurisdiction,
        }
    )


def normalize_context(
    *,
    supplier: SupplierEvidenceDTO | None,
    contract: ContractEvidenceDTO | None,
) -> dict[str, Any]:
    """Pure: `(supplier, contract) -> context`. See module docstring."""
    context: dict[str, Any] = {}
    supplier_ctx = _supplier_context(supplier)
    if supplier_ctx:
        context["supplier"] = supplier_ctx
    contract_ctx = _contract_context(contract)
    if contract_ctx:
        context["contract"] = contract_ctx
    return context


async def build_context_for_contract_version(
    session: AsyncSession, *, organization_id: uuid.UUID, contract_version_id: uuid.UUID
) -> dict[str, Any]:
    """The side-effecting wrapper: resolves the `ContractVersion`'s `Supplier` (via
    `Contracts & Documents`' own `get_supplier_id_for_contract_version`), fetches both
    DTOs through their respective ports, and normalizes them. A `ContractVersion` that
    doesn't resolve to a supplier (not found / cross-tenant) simply yields no
    `supplier.*` context, same as `get_normalized_profile` returning `None`."""
    contract = await get_normalized_terms(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    )
    supplier_id = await get_supplier_id_for_contract_version(
        session, organization_id=organization_id, contract_version_id=contract_version_id
    )
    supplier = None
    if supplier_id is not None:
        supplier = await get_normalized_profile(
            session, organization_id=organization_id, supplier_id=supplier_id
        )
    return normalize_context(supplier=supplier, contract=contract)
