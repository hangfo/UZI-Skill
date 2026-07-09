from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
sys.path.insert(0, str(SCRIPTS))
TOOL = ROOT / "tools" / "branch_score_compare.py"
spec = importlib.util.spec_from_file_location("branch_score_compare", TOOL)
branch_score_compare = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(branch_score_compare)


def test_decision_tier_boundaries():
    assert branch_score_compare.decision_tier(39.9) == "avoid"
    assert branch_score_compare.decision_tier(40.0) == "cautious"
    assert branch_score_compare.decision_tier(55.0) == "watch"
    assert branch_score_compare.decision_tier(65.0) == "buy_candidate"
    assert branch_score_compare.decision_tier(80.0) == "strong_buy"


def test_quality_control_downgrade_is_possible_regression():
    case = {"ticker": "AAPL", "expectation": "quality_control", "min_candidate_score": 60.0}
    row = branch_score_compare.compare_scores(
        case,
        {"investment_score": 66.0},
        {"investment_score": 54.0},
    )
    assert row["verdict"] == "possible_regression"
    assert "quality_control_downgrade" in row["flags"]
    assert "below_candidate_floor" in row["flags"]


def test_risk_control_score_drop_is_ok():
    case = {"ticker": "MSTR", "expectation": "risk_control", "max_candidate_score": 45.0}
    row = branch_score_compare.compare_scores(
        case,
        {"investment_score": 43.0},
        {"investment_score": 34.0},
    )
    assert row["verdict"] == "review"
    assert "large_score_drift" in row["flags"]
    assert "risk_control_upgrade" not in row["flags"]
    assert row["explanation"]["category"] == "risk_control_reasonable_tightening"
    assert row["explanation"]["metrics"]["nearest_boundary_distance"] == 11.0


def test_risk_control_upgrade_is_possible_regression():
    case = {"ticker": "AXTI", "expectation": "risk_control", "max_candidate_score": 45.0}
    row = branch_score_compare.compare_scores(
        case,
        {"investment_score": 38.0},
        {"investment_score": 56.0},
    )
    assert row["verdict"] == "possible_regression"
    assert "risk_control_upgrade" in row["flags"]
    assert "above_candidate_ceiling" in row["flags"]
    assert row["explanation"]["category"] == "risk_control_suspicious_upgrade"
    assert row["explanation"]["metrics"]["boundary_violations"][0]["margin"] == -11.0


def test_speculative_watch_promoted_to_buy_is_possible_regression():
    case = {"ticker": "688017.SH", "expectation": "speculative_watch", "max_candidate_score": 65.0}
    row = branch_score_compare.compare_scores(
        case,
        {"investment_score": 58.0},
        {"investment_score": 66.0},
    )
    assert row["verdict"] == "possible_regression"
    assert "speculative_promoted_to_buy" in row["flags"]
    assert row["explanation"]["category"] == "speculative_promoted_to_buy"


def test_dim_score_ceiling_violation_is_possible_regression():
    case = {
        "ticker": "__synthetic_empty_recent_news_stale_legacy",
        "expectation": "neutral",
        "max_candidate_dim_scores": {"15_events": 5.0},
    }
    row = branch_score_compare.compare_scores(
        case,
        {"investment_score": 55.0, "dim_scores": {"15_events": 5}},
        {"investment_score": 55.0, "dim_scores": {"15_events": 8}},
    )
    assert row["verdict"] == "possible_regression"
    assert "15_events_above_ceiling" in row["flags"]
    assert row["explanation"]["category"] == "field_contract_violation"


def test_dim_score_floor_violation_is_possible_regression():
    case = {
        "ticker": "__synthetic_negated_negative_event",
        "expectation": "neutral",
        "min_candidate_dim_scores": {"15_events": 5.0},
    }
    row = branch_score_compare.compare_scores(
        case,
        {"investment_score": 55.0, "dim_scores": {"15_events": 5}},
        {"investment_score": 55.0, "dim_scores": {"15_events": 4}},
    )
    assert row["verdict"] == "possible_regression"
    assert "15_events_below_floor" in row["flags"]
    assert row["explanation"]["category"] == "field_contract_violation"


def test_near_boundary_lowers_confidence():
    case = {"ticker": "AAPL", "expectation": "quality_control", "min_candidate_score": 60.0}
    row = branch_score_compare.compare_scores(
        case,
        {"investment_score": 62.0},
        {"investment_score": 60.5},
    )
    assert row["verdict"] == "ok"
    assert row["explanation"]["confidence"]["level"] == "medium"
    assert "候选结果距离边界 <= 1 分" in row["explanation"]["confidence"]["factors"]
    assert row["explanation"]["metrics"]["threshold_sensitivity"]["level"] == "high"


def test_stage_guardrail_tightening_has_explainable_category():
    case = {
        "name": "high_quality_stage3_confirmed_downtrend",
        "role": "quality stock in confirmed distribution/downtrend",
        "expectation": "speculative_watch",
        "max_candidate_score": 64.0,
    }
    row = branch_score_compare.compare_scores(
        case,
        {"investment_score": 66.0},
        {"investment_score": 59.0},
    )
    assert row["verdict"] == "review"
    assert row["explanation"]["category"] == "trend_guardrail_tightening"
    assert row["explanation"]["confidence"]["level"] == "high"


def test_compare_outputs_includes_reason_and_confidence_summary():
    payload = {
        "raw_items": [
            {"mode": "lite", "case": {"ticker": "AAPL", "expectation": "quality_control", "min_candidate_score": 60.0}}
        ],
        "synthetic_cases": [],
    }
    baseline = {"ref": "base", "raw": [{"case": "AAPL", "mode": "lite", "investment_score": 62.0}]}
    candidate = {"ref": "cand", "raw": [{"case": "AAPL", "mode": "lite", "investment_score": 60.5}]}
    result = branch_score_compare.compare_outputs(payload, baseline, candidate)
    assert result["reason_summary"]["stable_no_material_change"] == 1
    assert result["confidence_summary"]["medium"] == 1
    assert result["support_summary"]["isolated"] == 1
    assert result["reliability_summary"]["low"] == 1
    row = result["raw_comparisons"][0]
    assert row["explanation"]["reliability"]["level"] == "low"


def test_cross_support_is_strong_when_cached_synthetic_and_modes_agree():
    payload = {
        "raw_items": [
            {
                "mode": "lite",
                "case": {"ticker": "MSTR", "group": "core", "expectation": "risk_control", "max_candidate_score": 45.0},
            },
            {
                "mode": "medium",
                "case": {"ticker": "MSTR", "group": "core", "expectation": "risk_control", "max_candidate_score": 45.0},
            },
            {
                "mode": "lite",
                "case": {
                    "ticker": "__synthetic_missing_financials_raw",
                    "group": "synthetic_raw",
                    "expectation": "risk_control",
                    "max_candidate_score": 65.0,
                },
            },
        ],
        "synthetic_cases": [
            {
                "name": "theme_only_microcap",
                "expectation": "risk_control",
                "features": {},
                "max_candidate_score": 58.0,
            }
        ],
    }
    baseline = {
        "ref": "base",
        "raw": [
            {"case": "MSTR", "mode": "lite", "investment_score": 43.0},
            {"case": "MSTR", "mode": "medium", "investment_score": 43.0},
            {"case": "__synthetic_missing_financials_raw", "mode": "lite", "investment_score": 58.0},
        ],
        "synthetic": [{"case": "theme_only_microcap", "investment_score": 50.0}],
    }
    candidate = {
        "ref": "cand",
        "raw": [
            {"case": "MSTR", "mode": "lite", "investment_score": 34.0},
            {"case": "MSTR", "mode": "medium", "investment_score": 34.0},
            {"case": "__synthetic_missing_financials_raw", "mode": "lite", "investment_score": 54.0},
        ],
        "synthetic": [{"case": "theme_only_microcap", "investment_score": 42.0}],
    }
    result = branch_score_compare.compare_outputs(payload, baseline, candidate)
    assert result["support_summary"]["strong"] == 4
    assert result["reliability_summary"]["high"] == 4
    for row in result["raw_comparisons"] + result["synthetic_comparisons"]:
        assert row["explanation"]["support"]["level"] == "strong"
        assert row["explanation"]["reliability"]["level"] == "high"


def test_cross_support_is_limited_for_synthetic_only_repeated_category():
    payload = {
        "raw_items": [],
        "synthetic_cases": [
            {
                "name": "high_quality_stage3_confirmed_downtrend",
                "role": "quality stock in confirmed distribution/downtrend",
                "expectation": "speculative_watch",
                "features": {},
                "max_candidate_score": 64.0,
            },
            {
                "name": "stage4_missing_price_high_quality",
                "role": "Stage 4 quality stock with missing price confirmation",
                "expectation": "speculative_watch",
                "features": {},
                "max_candidate_score": 64.0,
            },
        ],
    }
    baseline = {
        "ref": "base",
        "synthetic": [
            {"case": "high_quality_stage3_confirmed_downtrend", "investment_score": 66.0},
            {"case": "stage4_missing_price_high_quality", "investment_score": 66.0},
        ],
    }
    candidate = {
        "ref": "cand",
        "synthetic": [
            {"case": "high_quality_stage3_confirmed_downtrend", "investment_score": 59.0},
            {"case": "stage4_missing_price_high_quality", "investment_score": 59.0},
        ],
    }
    result = branch_score_compare.compare_outputs(payload, baseline, candidate)
    assert result["support_summary"]["limited"] == 2
    assert {row["explanation"]["support"]["level"] for row in result["synthetic_comparisons"]} == {"limited"}
    assert result["reliability_summary"] == {"medium": 2}


def test_build_payload_includes_synthetic_raw_cases():
    payload = branch_score_compare.build_payload(
        modes=["lite"],
        raw_cases=[],
        synthetic_cases=branch_score_compare.SYNTHETIC_CASES,
    )
    tickers = {item["case"]["ticker"] for item in payload["raw_items"]}
    assert "__synthetic_empty_recent_news_stale_legacy" in tickers
    assert "__synthetic_single_strong_negative_event" in tickers
    assert "__synthetic_missing_financials_raw" in tickers


def test_adversarial_suite_has_data_quality_cases():
    names = {case["name"] for case in branch_score_compare.SYNTHETIC_CASES}
    assert "stage4_missing_price_high_quality" in names
    assert "missing_financials_theme_heat" in names
    raw_tickers = {case["ticker"] for case in branch_score_compare.SYNTHETIC_RAW_CASES}
    assert "__synthetic_missing_financials_raw" in raw_tickers


def test_classify_cached_blindspot_detects_stage_and_missing_financials():
    raw = branch_score_compare._minimal_raw(
        "TEST",
        {
            "1_financials": {"data": {}},
            "2_kline": {"data": {"stage": "Stage 4 下跌"}},
        },
    )
    case = branch_score_compare.classify_cached_blindspot("TEST", raw)
    assert case is not None
    assert case["group"] == "discovered_cache"
    assert case["expectation"] == "data_gap"
    assert "missing_financials" in case["blindspot_tags"]
    assert "stage3_4" in case["blindspot_tags"]


def test_classify_cached_blindspot_detects_negative_event_without_manual_pick():
    raw = branch_score_compare._minimal_raw(
        "TEST",
        {
            "15_events": {"data": {"recent_news": [{"title": "SEC charges accounting fraud against executives"}]}},
        },
    )
    case = branch_score_compare.classify_cached_blindspot("TEST", raw)
    assert case is not None
    assert case["expectation"] == "negative_event"
    assert "negative_event" in case["blindspot_tags"]


def test_discovered_cache_counts_as_cached_raw_support():
    row = {"group": "discovered_cache"}
    assert branch_score_compare._evidence_type(row) == "cached_raw"


def test_performance_warning_does_not_change_verdict():
    payload = {
        "raw_items": [
            {"mode": "lite", "case": {"ticker": "600519.SH", "expectation": "quality_control", "min_candidate_score": 55.0}}
        ],
        "synthetic_cases": [],
    }
    baseline = {
        "ref": "base",
        "raw": [{"case": "600519.SH", "mode": "lite", "investment_score": 59.0, "elapsed_sec": 88.0}],
    }
    candidate = {
        "ref": "cand",
        "raw": [{"case": "600519.SH", "mode": "lite", "investment_score": 59.0, "elapsed_sec": 80.0}],
    }
    result = branch_score_compare.compare_outputs(payload, baseline, candidate)
    assert result["summary"]["ok"] == 1
    assert len(result["performance_warnings"]) == 2


def test_quant_signal_offline_mode_does_not_autofetch():
    from lib import quant_signal

    old_env = os.environ.get("UZI_SCORING_OFFLINE")
    try:
        os.environ["UZI_SCORING_OFFLINE"] = "1"
        result = quant_signal.detect_quant_signal("600519.SH", fund_managers=None)
        assert result["active_funds_total"] == 0
        assert result["is_quant_factor_style"] is False
    finally:
        if old_env is None:
            os.environ.pop("UZI_SCORING_OFFLINE", None)
        else:
            os.environ["UZI_SCORING_OFFLINE"] = old_env


if __name__ == "__main__":
    import inspect
    import sys

    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not inspect.isfunction(fn):
            continue
        try:
            fn()
            print(f"PASS {name}")
            passed += 1
        except Exception as exc:
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
            failed += 1
    print(f"{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
