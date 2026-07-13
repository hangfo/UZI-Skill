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
    assert "__synthetic_verified_structured_p1" in tickers
    assert "__synthetic_forged_structured_p1" in tickers
    assert "__synthetic_resolved_structured_p1" in tickers
    assert "__synthetic_out_of_window_structured_p1" in tickers


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


def test_evidence_overlay_counts_as_frozen_overlay_not_cached_raw():
    row = {"group": "evidence_overlay"}
    assert branch_score_compare._evidence_type(row) == "frozen_overlay"


def test_ready_negative_event_overlay_becomes_raw_case_without_cache():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "SMCI",
        "target": "negative_event",
        "status": "ready",
        "evidence": [
            {
                "title": "SMCI 8-K Item 3.01: Notice of Delisting",
                "url": "https://www.sec.gov/example",
                "source": "sec_submissions",
                "published_at": "2025-02-26",
                "severity": "P1",
                "event_type": "sec_8k_item",
            }
        ],
    }
    case = branch_score_compare.overlay_to_raw_case(overlay)
    assert case is not None
    assert case["group"] == "evidence_overlay"
    assert case["ticker"] == "__overlay_SMCI_negative_event"
    assert case["max_candidate_score"] == 65.0
    assert case["max_candidate_dim_scores"]["15_events"] == 5.5
    payload = branch_score_compare.build_payload(["lite"], [case], [])
    assert payload["missing"] == []
    assert payload["raw_items"][0]["case"]["overlay_source_ticker"] == "SMCI"


def test_verified_resolved_overlay_is_non_harm_control_not_active_risk():
    event_id = "sec_submissions:active"
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "SMCI",
        "market": "US",
        "target": "negative_event",
        "status": "ready",
        "evidence": [
            {
                "title": "SMCI Item 3.01 prior noncompliance",
                "url": "https://www.sec.gov/Archives/edgar/data/1375365/active.htm",
                "source": "sec_submissions",
                "published_at": "2024-09-20",
                "severity": "P1",
                "event_type": "sec_8k_item",
                "official_source": True,
                "entity_match": "exact",
                "entity_scope": "issuer",
                "source_record_id": "active",
                "canonical_event_id": event_id,
                "resolution_status": "closed",
                "lifecycle_topic": "nasdaq_periodic_reporting_rule_5250_c_1",
                "resolution_evidence": {
                    "resolution_status": "closed",
                    "official_source": True,
                    "entity_match": "exact",
                    "entity_scope": "issuer",
                    "url": "https://www.sec.gov/Archives/edgar/data/1375365/closed.htm",
                    "published_at": "2025-02-26",
                    "source_record_id": "closed",
                    "linked_event_id": event_id,
                    "lifecycle_topic": "nasdaq_periodic_reporting_rule_5250_c_1",
                },
            }
        ],
    }

    case = branch_score_compare.overlay_to_raw_case(overlay)

    assert case is not None
    assert case["expectation"] == "resolved_negative_event"
    assert case["overlay_active_severities"] == []
    assert case["overlay_resolved_severities"] == ["P1"]
    assert case["min_candidate_dim_scores"]["15_events"] == 5.0


def test_cross_issuer_official_resolution_stays_active_overlay_risk():
    event_id = "sec_submissions:active"
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "SMCI",
        "market": "US",
        "target": "negative_event",
        "status": "ready",
        "evidence": [
            {
                "title": "SMCI Item 3.01 prior noncompliance",
                "url": "https://www.sec.gov/Archives/edgar/data/1375365/active.htm",
                "published_at": "2024-09-20",
                "severity": "P1",
                "official_source": True,
                "entity_match": "exact",
                "entity_scope": "issuer",
                "source_record_id": "active",
                "canonical_event_id": event_id,
                "resolution_status": "closed",
                "lifecycle_topic": "nasdaq_periodic_reporting_rule_5250_c_1",
                "resolution_evidence": {
                    "resolution_status": "closed",
                    "official_source": True,
                    "entity_match": "exact",
                    "entity_scope": "issuer",
                    "url": "https://www.sec.gov/Archives/edgar/data/320193/closed.htm",
                    "published_at": "2025-02-26",
                    "source_record_id": "closed",
                    "linked_event_id": event_id,
                    "lifecycle_topic": "nasdaq_periodic_reporting_rule_5250_c_1",
                },
            }
        ],
    }

    case = branch_score_compare.overlay_to_raw_case(overlay)

    assert case is not None
    assert case["expectation"] == "negative_event"
    assert case["overlay_active_severities"] == ["P1"]


def test_unverified_resolution_claim_remains_active_overlay_risk():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "SMCI",
        "market": "US",
        "target": "negative_event",
        "status": "ready",
        "evidence": [
            {
                "title": "SMCI Item 3.01 prior noncompliance",
                "url": "https://www.sec.gov/Archives/active.htm",
                "published_at": "2024-09-20",
                "severity": "P1",
                "official_source": True,
                "entity_match": "exact",
                "entity_scope": "issuer",
                "source_record_id": "active",
                "canonical_event_id": "sec_submissions:active",
                "resolution_status": "closed",
            }
        ],
    }

    case = branch_score_compare.overlay_to_raw_case(overlay)

    assert case is not None
    assert case["expectation"] == "negative_event"
    assert case["overlay_active_severities"] == ["P1"]
    assert case["max_candidate_score"] == 65.0


def test_mixed_active_and_resolved_overlay_adds_realistic_resolution_shadow_cases():
    event_id = "sec_submissions:resolved-event"
    resolved = {
        "title": "Prior Nasdaq periodic-report noncompliance",
        "url": "https://www.sec.gov/Archives/edgar/data/1375365/resolved-event.htm",
        "published_at": "2024-09-20",
        "severity": "P1",
        "official_source": True,
        "entity_match": "exact",
        "entity_scope": "issuer",
        "source_record_id": "resolved-event",
        "canonical_event_id": event_id,
        "resolution_status": "closed",
        "lifecycle_topic": "nasdaq_periodic_reporting_rule_5250_c_1",
        "age_days": 661,
        "resolution_evidence": {
            "resolution_status": "closed",
            "official_source": True,
            "entity_match": "exact",
            "entity_scope": "issuer",
            "url": "https://www.sec.gov/Archives/edgar/data/1375365/resolution.htm",
            "published_at": "2025-02-26",
            "source_record_id": "resolution",
            "linked_event_id": event_id,
            "lifecycle_topic": "nasdaq_periodic_reporting_rule_5250_c_1",
        },
    }
    active = {
        "title": "Unresolved auditor resignation",
        "url": "https://www.sec.gov/Archives/active-auditor.htm",
        "published_at": "2024-11-18",
        "severity": "P1",
        "official_source": True,
        "entity_match": "exact",
        "entity_scope": "issuer",
        "source_record_id": "active-auditor",
        "canonical_event_id": "sec_submissions:active-auditor",
        "resolution_status": "unknown",
        "age_days": 602,
    }
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "SMCI",
        "market": "US",
        "target": "negative_event",
        "status": "ready",
        "as_of": "2026-07-13",
        "evidence": [active, resolved],
    }

    cases = branch_score_compare.overlay_to_raw_cases(overlay)
    by_expectation = {}
    for case in cases:
        by_expectation.setdefault(case["expectation"], []).append(case)

    assert len(cases) == 4
    assert len(by_expectation["negative_event"]) == 2
    assert len(by_expectation["resolved_negative_event"]) == 2
    assert any(case["ticker"] == "__overlayres_SMCI_negative_event" for case in cases)
    assert any(case["ticker"].endswith("_resolution") for case in cases)


def test_p0_negative_event_overlay_has_stricter_boundary_than_p1():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "BAD",
        "target": "negative_event",
        "status": "ready",
        "evidence": [
            {
                "title": "BAD 8-K Item 4.02: Non-Reliance on Previously Issued Financial Statements",
                "url": "https://www.sec.gov/example",
                "source": "sec_submissions",
                "published_at": "2025-02-26",
                "severity": "P0",
                "event_type": "sec_8k_item",
            }
        ],
    }
    case = branch_score_compare.overlay_to_raw_case(overlay)
    assert case is not None
    assert case["max_candidate_score"] == 60.0
    assert case["max_candidate_dim_scores"]["15_events"] == 4.9


def test_gap_overlay_is_not_promoted_to_branch_case():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "AAPL",
        "target": "negative_event",
        "status": "gap",
        "evidence": [],
    }
    assert branch_score_compare.overlay_to_raw_case(overlay) is None


def test_unofficial_overlay_url_is_rejected_even_when_marked_ready():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "BAD",
        "target": "negative_event",
        "status": "ready",
        "evidence": [
            {
                "title": "Unverified penalty",
                "url": "https://example.com/penalty",
                "severity": "P1",
                "official_source": True,
                "entity_match": "exact",
            }
        ],
    }
    assert branch_score_compare.overlay_to_raw_case(overlay) is None


def test_p2_only_overlay_cannot_enter_branch_comparison_even_if_status_is_wrong():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "00171.HK",
        "market": "HK",
        "target": "negative_event",
        "status": "ready",
        "evidence": [
            {
                "title": "HKEX action against a former director",
                "url": "https://www.hkex.com.hk/example",
                "severity": "P2",
                "official_source": True,
                "entity_match": "exact",
                "entity_scope": "related_person",
            }
        ],
    }
    assert branch_score_compare.overlay_to_raw_case(overlay) is None


def test_a_and_hk_official_overlays_preserve_market_and_entity_metadata():
    for ticker, market, url in (
        ("002038.SZ", "A", "https://www.szse.cn/UpFiles/example.pdf"),
        ("03616.HK", "HK", "https://www.hkex.com.hk/News/example"),
    ):
        overlay = {
            "schema_version": "uzi.evidence_overlay.v1",
            "ticker": ticker,
            "market": market,
            "target": "negative_event",
            "status": "ready",
            "as_of": "2026-07-13",
            "lookback_days": 730,
            "evidence": [
                {
                    "title": "Official issuer disciplinary action",
                    "url": url,
                    "source": "official_adapter",
                    "published_at": "2026-04-29",
                    "severity": "P1",
                    "event_type": "issuer_discipline",
                    "official_source": True,
                    "entity_match": "exact",
                    "entity_scope": "issuer",
                    "match_method": "stock_code",
                    "age_days": 75,
                }
            ],
        }
        case = branch_score_compare.overlay_to_raw_case(overlay)
        assert case is not None
        assert case["overlay_market"] == market
        event = case["raw"]["dimensions"]["15_events"]["data"]["recent_news"][0]
        assert event["entity_scope"] == "issuer"
        assert event["match_method"] == "stock_code"
        assert event["official_source"] is True
        assert event["entity_match"] == "exact"


def test_duplicate_official_overlay_urls_only_enter_once():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "002038.SZ",
        "market": "A",
        "target": "negative_event",
        "status": "ready",
        "evidence": [
            {
                "title": "Same decision",
                "url": "https://www.szse.cn/UpFiles/same.pdf",
                "severity": severity,
                "official_source": True,
                "entity_match": "exact",
            }
            for severity in ("P2", "P1")
        ],
    }
    case = branch_score_compare.overlay_to_raw_case(overlay)
    assert case is not None
    news = case["raw"]["dimensions"]["15_events"]["data"]["recent_news"]
    assert len(news) == 1
    assert news[0]["severity"] == "P1"


def test_ready_overlay_adds_market_matched_counterfactual_without_mutating_cached_raw():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "SMCI",
        "market": "US",
        "target": "negative_event",
        "status": "ready",
        "as_of": "2026-07-13",
        "lookback_days": 730,
        "evidence": [
            {
                "title": "SMCI 8-K Item 3.01: Notice of Delisting",
                "url": "https://www.sec.gov/example",
                "source": "sec_submissions",
                "published_at": "2025-02-26",
                "severity": "P1",
                "event_type": "sec_8k_item",
                "official_source": True,
                "entity_match": "exact",
                "entity_scope": "issuer",
            }
        ],
    }
    cached_path = branch_score_compare.CACHE / "AAPL" / "raw_data.json"
    before = cached_path.read_bytes()
    cases = branch_score_compare.overlay_to_raw_cases(overlay)
    assert len(cases) == 2
    counterfactual = next(case for case in cases if case.get("counterfactual_base_ticker") == "AAPL")
    assert counterfactual["max_candidate_score"] == 64.9
    assert "1_financials" in counterfactual["raw"]["dimensions"]
    event_data = counterfactual["raw"]["dimensions"]["15_events"]["data"]
    assert any("Notice of Delisting" in item.get("title", "") for item in event_data["recent_news"])
    assert event_data["evidence_overlay"]["counterfactual_base"] == "AAPL"
    assert cached_path.read_bytes() == before


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


def test_market_for_ticker_is_cross_market_and_deterministic():
    assert branch_score_compare.market_for_ticker("600519.SH") == "A"
    assert branch_score_compare.market_for_ticker("00700.HK") == "HK"
    assert branch_score_compare.market_for_ticker("AAPL") == "US"
    assert branch_score_compare.market_for_ticker("2330.TW") == "TW"
    assert branch_score_compare.market_for_ticker("7203.T") == "JP"
    assert branch_score_compare.market_for_ticker("SIVE.ST") == "EU"


def test_cache_blindspot_audit_reports_real_cache_gaps_without_synthetic_credit():
    cases = [
        {
            "ticker": "600519.SH",
            "market": "A",
            "group": "discovered_cache",
            "expectation": "speculative_watch",
            "blindspot_tags": ["stage3_4"],
        },
        {
            "ticker": "AAPL",
            "market": "US",
            "group": "synthetic_raw",
            "expectation": "negative_event",
            "blindspot_tags": ["negative_event"],
        },
    ]
    audit = branch_score_compare.build_cache_blindspot_audit(cases)
    by_target = {row["target"]: row for row in audit["coverage"]}
    assert by_target["stage3_4"]["cached_raw_count"] == 1
    assert by_target["stage3_4"]["status"] == "gap"
    assert by_target["negative_event"]["cached_raw_count"] == 0
    assert by_target["negative_event"]["status"] == "gap"
    assert by_target["negative_event"]["missing_cases"] == 2
    assert "online_backfill_plan" in by_target["negative_event"]


def test_online_backfill_plan_is_source_first_and_frozen():
    audit = branch_score_compare.build_cache_blindspot_audit([])
    by_target = {row["target"]: row for row in audit["coverage"]}
    plan = by_target["negative_event"]["online_backfill_plan"][0]
    assert "official" in plan["selection_rule"]
    assert "score changed" in plan["selection_rule"]
    assert plan["freeze_output"].endswith("evidence-overlays/<ticker>.json")
    assert "do not infer" in plan["rejection_rule"]
    assert any("frozen" in item.lower() for item in audit["online_offline_balance"]["promotion_gate"])


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
