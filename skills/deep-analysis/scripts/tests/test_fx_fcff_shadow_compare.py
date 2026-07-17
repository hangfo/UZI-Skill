from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


def test_fx_contract_requires_fresh_inverse_and_triangle_agreement():
    from fx_fcff_shadow_compare import validate_fx_contract

    valid = validate_fx_contract(
        direct_rate=1.16, inverse_rate=1 / 1.1598, triangle_rate=1.1605,
        as_of="2026-07-17", today=date(2026, 7, 17),
        official_rate=1.1595, official_market_rate=1.16,
        official_as_of="2026-07-17",
    )
    assert valid["eligible"] is True
    assert valid["inverse_gap_pct"] < 0.5
    assert valid["triangle_gap_pct"] < 0.75

    stale = validate_fx_contract(
        direct_rate=1.16, inverse_rate=1 / 1.16, triangle_rate=1.16,
        as_of="2026-07-01", today=date(2026, 7, 17),
        official_rate=1.16, official_market_rate=1.16,
        official_as_of="2026-07-01",
    )
    assert stale["eligible"] is False
    assert "stale_or_future_fx_observation" in stale["gates"]

    inconsistent = validate_fx_contract(
        direct_rate=1.16, inverse_rate=0.80, triangle_rate=1.05,
        as_of="2026-07-17", today=date(2026, 7, 17),
        official_rate=1.10, official_market_rate=1.16,
        official_as_of="2026-07-17",
    )
    assert inconsistent["eligible"] is False
    assert "inverse_identity_gap" in inconsistent["gates"]
    assert "triangle_cross_gap" in inconsistent["gates"]
    assert "official_cross_source_gap" in inconsistent["gates"]


def test_fcff_reconstruction_never_promotes_unverified_accounting_policy():
    from fx_fcff_shadow_compare import reconstruct_fcff

    result = reconstruct_fcff({
        "ebit": 120.0,
        "tax_provision": 20.0,
        "pretax_income": 100.0,
        "depreciation_amortization": 10.0,
        "signed_capex": -15.0,
        "change_working_capital": -5.0,
        "levered_fcf": 80.0,
        "interest_expense": 10.0,
    })
    assert result["partial_ebit_bridge"] == 86.0
    assert result["after_tax_interest_bridge"] == 88.0
    assert result["method_gap_pct"] < 10
    assert result["production_eligible"] is False
    assert "interest_cashflow_classification_unverified" in result["gates"]


def test_fcff_reconstruction_preserves_missing_and_invalid_inputs():
    from fx_fcff_shadow_compare import reconstruct_fcff

    result = reconstruct_fcff({
        "ebit": -10.0,
        "tax_provision": -2.0,
        "pretax_income": -8.0,
        "depreciation_amortization": 1.0,
        "signed_capex": -3.0,
        "change_working_capital": None,
        "levered_fcf": -12.0,
        "interest_expense": 2.0,
    })
    assert result["effective_tax_rate"] is None
    assert result["partial_ebit_bridge"] is None
    assert result["after_tax_interest_bridge"] is None
    assert "invalid_effective_tax_rate" in result["gates"]
    assert "fcff_methods_gap_gt_10pct" in result["gates"]
