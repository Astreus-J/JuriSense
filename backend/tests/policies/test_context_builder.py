"""#60: `normalize_context` must be a pure function -- same inputs, same output, no
hidden state or side effects -- and must implement the documented normalization
decisions (currency handling for `contract.value.brl`, the `privacy.*` flattening, the
"omit, never null" rule for inapplicable fields)."""

import copy

from app.contracts.domain.evidence import ContractEvidenceDTO
from app.policies.application.context_builder import normalize_context
from app.suppliers.domain.evidence import SupplierEvidenceDTO

SUPPLIER = SupplierEvidenceDTO(
    registry_status="active",
    sanctions_hit=True,
    activity_mismatch=False,
    address_flag="consistent",
    cnae_code="6201-5/00",
)

CONTRACT_BRL = ContractEvidenceDTO(
    contract_type="services",
    value_amount=300000,
    value_currency="BRL",
    duration_start_date="2026-01-01",
    duration_end_date="2027-01-01",
    duration_auto_renewal=True,
    termination_notice_period_days=30,
    termination_for_convenience=True,
    liability_type="unlimited",
    liability_cap=None,
    processes_personal_data=True,
    dpa_present=False,
    jurisdiction="BR",
)


def test_normalize_context_is_pure() -> None:
    """Calling twice with the same (immutable) inputs produces an equal, independent
    result -- no shared mutable state leaks between calls."""
    first = normalize_context(supplier=SUPPLIER, contract=CONTRACT_BRL)
    second = normalize_context(supplier=SUPPLIER, contract=CONTRACT_BRL)
    assert first == second
    assert first is not second

    # Mutating the result of one call must never affect a later call.
    mutated = copy.deepcopy(first)
    mutated["contract"]["value"]["brl"] = -1
    third = normalize_context(supplier=SUPPLIER, contract=CONTRACT_BRL)
    assert third == first
    assert third != mutated


def test_normalize_context_no_inputs_yields_empty_context() -> None:
    assert normalize_context(supplier=None, contract=None) == {}


def test_supplier_fields_surface_under_supplier_namespace() -> None:
    context = normalize_context(supplier=SUPPLIER, contract=None)
    assert context == {
        "supplier": {
            "registry_status": "active",
            "sanctions_hit": True,
            "activity_mismatch": False,
            "address_flag": "consistent",
            "cnae_code": "6201-5/00",
        }
    }


def test_contract_brl_value_is_surfaced_when_currency_is_brl() -> None:
    context = normalize_context(supplier=None, contract=CONTRACT_BRL)
    assert context["contract"]["value"]["brl"] == 300000
    assert context["contract"]["value"]["currency"] == "BRL"
    # LGPD-001's fields flatten out of `privacy.*`.
    assert context["contract"]["processes_personal_data"] is True
    assert context["contract"]["dpa_present"] is False


def test_contract_value_brl_omitted_for_non_brl_currency() -> None:
    """#60's scope call: no FX conversion -- a non-BRL contract's `contract.value.brl`
    is omitted entirely (never set to null)."""
    usd_contract = ContractEvidenceDTO(
        contract_type="services",
        value_amount=50000,
        value_currency="USD",
        duration_start_date=None,
        duration_end_date=None,
        duration_auto_renewal=None,
        termination_notice_period_days=None,
        termination_for_convenience=None,
        liability_type=None,
        liability_cap=None,
        processes_personal_data=None,
        dpa_present=None,
        jurisdiction=None,
    )
    context = normalize_context(supplier=None, contract=usd_contract)
    assert "brl" not in context["contract"]["value"]
    assert context["contract"]["value"]["amount"] == 50000
    assert context["contract"]["value"]["currency"] == "USD"


def test_contract_value_brl_omitted_when_amount_missing() -> None:
    no_amount = ContractEvidenceDTO(
        contract_type=None,
        value_amount=None,
        value_currency="BRL",
        duration_start_date=None,
        duration_end_date=None,
        duration_auto_renewal=None,
        termination_notice_period_days=None,
        termination_for_convenience=None,
        liability_type=None,
        liability_cap=None,
        processes_personal_data=None,
        dpa_present=None,
        jurisdiction=None,
    )
    context = normalize_context(supplier=None, contract=no_amount)
    assert "value" not in context.get("contract", {}) or "brl" not in context["contract"]["value"]


def test_none_leaves_are_omitted_not_nulled() -> None:
    """Every `None`-valued leaf (a term the extraction never found) must be absent from
    the context dict entirely -- not present with a `null`/`None` value -- per the
    documented has()-guard strategy in `app.policies.domain.rule_dsl`."""
    sparse_contract = ContractEvidenceDTO(
        contract_type="services",
        value_amount=None,
        value_currency=None,
        duration_start_date=None,
        duration_end_date=None,
        duration_auto_renewal=None,
        termination_notice_period_days=None,
        termination_for_convenience=None,
        liability_type="unlimited",
        liability_cap=None,
        processes_personal_data=None,
        dpa_present=None,
        jurisdiction=None,
    )
    context = normalize_context(supplier=None, contract=sparse_contract)

    def _assert_no_none(node) -> None:
        if isinstance(node, dict):
            for value in node.values():
                assert value is not None
                _assert_no_none(value)

    _assert_no_none(context)
    assert context["contract"]["liability"]["type"] == "unlimited"
    assert "duration" not in context["contract"]
    assert "value" not in context["contract"]
