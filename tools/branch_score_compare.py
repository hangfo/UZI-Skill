from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "run.py").exists() and (parent / "skills").exists():
            return parent
    raise RuntimeError("could not locate UZI-Skill repo root")


ROOT = _find_repo_root()
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
CACHE = SCRIPTS / ".cache"
OUT_DIR = ROOT / "local-ops" / "state" / "branch-score-compare"

CORE_DIMS = {
    "0_basic",
    "1_financials",
    "2_kline",
    "10_valuation",
    "11_governance",
    "15_events",
    "16_lhb",
}

RAW_CASES = [
    {
        "ticker": "600519.SH",
        "group": "core",
        "role": "A-share quality/value control",
        "expectation": "quality_control",
        "min_candidate_score": 55.0,
    },
    {
        "ticker": "00700.HK",
        "group": "core",
        "role": "HK platform quality control",
        "expectation": "quality_control",
        "min_candidate_score": 55.0,
    },
    {
        "ticker": "AAPL",
        "group": "core",
        "role": "US profitable mega-cap with valuation constraint",
        "expectation": "quality_control",
        "min_candidate_score": 60.0,
    },
    {
        "ticker": "MSTR",
        "group": "core",
        "role": "crypto treasury / volatility risk control",
        "expectation": "risk_control",
        "max_candidate_score": 45.0,
    },
    {
        "ticker": "AXTI",
        "group": "core",
        "role": "speculative small-cap adversarial control",
        "expectation": "risk_control",
        "max_candidate_score": 45.0,
    },
    {
        "ticker": "CRCL",
        "group": "holdout",
        "role": "stablecoin / IPO volatility / regulatory catalyst holdout",
        "expectation": "risk_control",
        "max_candidate_score": 45.0,
    },
    {
        "ticker": "SIVE.ST",
        "group": "holdout",
        "role": "Swedish market compatibility and loss/high-valuation holdout",
        "expectation": "risk_control",
        "max_candidate_score": 45.0,
    },
    {
        "ticker": "688017.SH",
        "group": "holdout",
        "role": "robotics reducer growth with valuation pressure",
        "expectation": "speculative_watch",
        "max_candidate_score": 65.0,
    },
]

SYNTHETIC_CASES = [
    {
        "name": "theme_only_microcap",
        "role": "hot theme but weak quality and extreme risk",
        "expectation": "risk_control",
        "max_candidate_score": 58.0,
        "features": {
            "market": "US",
            "market_cap_yi": 30,
            "roe_5y_avg": 0,
            "net_margin": -18,
            "gross_margin": 15,
            "revenue_growth_3y_cagr": -5,
            "net_profit_growth_latest": -40,
            "pe": 0,
            "pb": 18,
            "stage_num": 2,
            "ytd_return": 420,
            "volatility_1y": 150,
            "max_drawdown_1y": -65,
            "ai_chokepoint_score": 95,
            "has_positive_catalyst": True,
            "is_safe": True,
        },
    },
    {
        "name": "quality_compounder_no_momentum",
        "role": "durable quality but weak trend and muted growth",
        "expectation": "quality_control",
        "min_candidate_score": 55.0,
        "max_candidate_score": 64.0,
        "features": {
            "market": "A",
            "market_cap_yi": 9000,
            "roe_5y_avg": 24,
            "roe_5y_min": 18,
            "net_margin": 32,
            "gross_margin": 55,
            "revenue_growth_3y_cagr": 6,
            "net_profit_growth_latest": 3,
            "pe": 16,
            "pb": 4,
            "pe_quantile_5y": 35,
            "stage_num": 4,
            "ytd_return": -12,
            "volatility_1y": 25,
            "max_drawdown_1y": -24,
            "is_safe": True,
        },
    },
    {
        "name": "expensive_profitable_platform",
        "role": "high quality platform with valuation pressure",
        "expectation": "speculative_watch",
        "min_candidate_score": 50.0,
        "max_candidate_score": 70.0,
        "features": {
            "market": "US",
            "market_cap_yi": 30000,
            "roe_5y_avg": 45,
            "net_margin": 28,
            "gross_margin": 70,
            "revenue_growth_3y_cagr": 12,
            "net_profit_growth_latest": 10,
            "pe": 55,
            "pb": 28,
            "stage_num": 2,
            "ytd_return": 35,
            "volatility_1y": 30,
            "max_drawdown_1y": -22,
            "is_safe": True,
        },
    },
    {
        "name": "high_quality_stage3_confirmed_downtrend",
        "role": "quality stock in confirmed distribution/downtrend",
        "expectation": "speculative_watch",
        "max_candidate_score": 64.0,
        "features": {
            "market": "A",
            "market_cap_yi": 12000,
            "roe_5y_avg": 28,
            "roe_5y_min": 20,
            "net_margin": 35,
            "gross_margin": 60,
            "revenue_growth_3y_cagr": 8,
            "net_profit_growth_latest": 6,
            "pe": 18,
            "pb": 5,
            "pe_quantile_5y": 30,
            "stage_num": 3,
            "ytd_return": -18,
            "volatility_1y": 28,
            "max_drawdown_1y": -28,
            "debt_ratio": 20,
            "is_safe": True,
        },
    },
    {
        "name": "stage4_missing_price_high_quality",
        "role": "Stage 4 quality stock with missing price confirmation",
        "expectation": "speculative_watch",
        "max_candidate_score": 59.0,
        "features": {
            "market": "US",
            "market_cap_yi": 50000,
            "roe_5y_avg": 30,
            "roe_5y_min": 20,
            "net_margin": 25,
            "gross_margin": 55,
            "revenue_growth_3y_cagr": 10,
            "net_profit_growth_latest": 8,
            "pe": 20,
            "pb": 5,
            "pe_quantile_5y": 40,
            "stage_num": 4,
            "volatility_1y": 25,
            "debt_ratio": 20,
            "is_safe": True,
        },
    },
    {
        "name": "a_share_youzi_heat_institutional_selling",
        "role": "A-share youzi heat with institutional selling and weak fundamentals",
        "expectation": "risk_control",
        "max_candidate_score": 55.0,
        "features": {
            "market": "A",
            "market_cap_yi": 120,
            "roe_5y_avg": 4,
            "roe_5y_min": -8,
            "net_margin": 3,
            "gross_margin": 18,
            "revenue_growth_3y_cagr": 3,
            "net_profit_growth_latest": -20,
            "pe": 80,
            "pb": 12,
            "pe_quantile_5y": 90,
            "stage_num": 2,
            "ytd_return": 160,
            "volatility_1y": 110,
            "max_drawdown_1y": -55,
            "debt_ratio": 65,
            "lhb_30d_count": 9,
            "is_safe": False,
        },
    },
    {
        "name": "missing_financials_theme_heat",
        "role": "missing fundamentals but high theme heat and analyst optimism",
        "expectation": "risk_control",
        "max_candidate_score": 55.0,
        "features": {
            "market": "US",
            "market_cap_yi": 80,
            "revenue_growth_3y_cagr": 0,
            "net_profit_growth_latest": 0,
            "pe": 0,
            "pb": 20,
            "stage_num": 2,
            "ytd_return": 220,
            "volatility_1y": 120,
            "max_drawdown_1y": -60,
            "ai_chokepoint_score": 90,
            "has_positive_catalyst": True,
            "buy_rating_pct": 90,
        },
    },
]


def _dim(data: dict[str, Any]) -> dict[str, Any]:
    return {"data": data}


def _minimal_raw(ticker: str, dims_override: dict[str, Any] | None = None) -> dict[str, Any]:
    dims: dict[str, Any] = {
        "0_basic": _dim({"name": ticker, "industry": "Technology", "price": 100.0, "pe_ttm": 20.0, "pb": 3.0}),
        "1_financials": _dim(
            {
                "roe": 15.0,
                "roe_history": [12, 14, 15],
                "net_margin": 15.0,
                "gross_margin": 40.0,
                "revenue_history": [800, 900, 1000, 1150],
                "financial_health": {"debt_ratio": 30.0},
            }
        ),
        "2_kline": _dim(
            {
                "stage": "Stage 2 · Markup",
                "ma_align": "多头排列",
                "kline_stats": {"max_drawdown": -15.0, "ytd_return": 12.0},
            }
        ),
        "3_macro": _dim({}),
        "4_peers": _dim({}),
        "5_chain": _dim({}),
        "6_research": _dim({"report_count": 10, "rating_distribution": {"买入": 6}}),
        "7_industry": _dim({}),
        "8_materials": _dim({}),
        "9_futures": _dim({}),
        "10_valuation": _dim({"pe": 20.0, "pe_ttm": 20.0, "pe_quantile": 50.0, "industry_pe": 25.0}),
        "11_governance": _dim({"pledge": [], "insider_trades_1y": []}),
        "12_capital_flow": _dim({"main_fund_flow_20d": [], "unlock_schedule": []}),
        "13_policy": _dim({}),
        "14_moat": _dim({}),
        "15_events": _dim({}),
        "16_lhb": _dim({"lhb_count_30d": 0, "matched_youzi": []}),
        "17_sentiment": _dim({"hot_rank": {"rank_history": []}}),
        "18_trap": _dim({}),
        "19_contests": _dim({"summary": {"xueqiu_cubes_total": 0, "high_return_cubes": 0}}),
    }
    for key, value in (dims_override or {}).items():
        dims[key] = value
    return {"ticker": ticker, "dimensions": dims}


SYNTHETIC_RAW_CASES = [
    {
        "ticker": "__synthetic_empty_recent_news_stale_legacy",
        "group": "synthetic_raw",
        "role": "canonical empty recent_news must not fall back to stale legacy news",
        "expectation": "neutral",
        "max_candidate_dim_scores": {"15_events": 5.0},
        "raw": _minimal_raw(
            "__synthetic_empty_recent_news_stale_legacy",
            {
                "15_events": _dim(
                    {
                        "recent_news": [],
                        "news": [{"title": f"stale cached positive item {i}"} for i in range(30)],
                        "recent_notices": [],
                    }
                )
            },
        ),
    },
    {
        "ticker": "__synthetic_single_strong_negative_event",
        "group": "synthetic_raw",
        "role": "one severe negative event must matter without requiring repetition",
        "expectation": "negative_event",
        "max_candidate_dim_scores": {"15_events": 4.9},
        "raw": _minimal_raw(
            "__synthetic_single_strong_negative_event",
            {
                "15_events": _dim(
                    {
                        "recent_news": [{"title": "SEC charges accounting fraud against executives"}],
                        "recent_notices": [],
                    }
                )
            },
        ),
    },
    {
        "ticker": "__synthetic_negated_negative_event",
        "group": "synthetic_raw",
        "role": "negated negative phrases should not be penalized as real events",
        "expectation": "neutral",
        "min_candidate_dim_scores": {"15_events": 5.0},
        "raw": _minimal_raw(
            "__synthetic_negated_negative_event",
            {
                "15_events": _dim(
                    {
                        "recent_news": [
                            {"title": "公司无违规记录"},
                            {"title": "未发现欺诈行为"},
                            {"title": "settled lawsuit已和解"},
                        ],
                        "recent_notices": [],
                    }
                )
            },
        ),
    },
    {
        "ticker": "__synthetic_missing_financials_raw",
        "group": "synthetic_raw",
        "role": "missing financials should not crash or promote a high-confidence buy",
        "expectation": "data_gap",
        "max_candidate_score": 65.0,
        "raw": _minimal_raw(
            "__synthetic_missing_financials_raw",
            {
                "1_financials": _dim({}),
                "6_research": _dim({"report_count": 30, "rating_distribution": {"买入": 25}}),
                "15_events": _dim({"recent_news": [{"title": f"positive catalyst {i}"} for i in range(25)]}),
            },
        ),
    },
]

DECISION_ORDER = {
    "avoid": 0,
    "cautious": 1,
    "watch": 2,
    "buy_candidate": 3,
    "strong_buy": 4,
}

REGRESSION_FLAGS = {
    "execution_error",
    "below_candidate_floor",
    "above_candidate_ceiling",
    "quality_control_downgrade",
    "risk_control_upgrade",
    "speculative_promoted_to_buy",
    "15_events_below_floor",
    "15_events_above_ceiling",
}

REASON_LABELS = {
    "execution_failure": "执行失败/输出缺失",
    "field_contract_violation": "字段契约违反",
    "quality_control_possible_downgrade": "质量样本疑似误降级",
    "risk_control_suspicious_upgrade": "风险样本疑似误升级",
    "speculative_promoted_to_buy": "投机样本被推成买入",
    "risk_control_reasonable_tightening": "风险控制合理收紧",
    "trend_guardrail_tightening": "趋势护栏合理收紧",
    "data_quality_uncertain": "数据质量边界需复核",
    "material_score_drift": "大幅分数漂移",
    "decision_tier_shift": "买卖档位变化",
    "stable_no_material_change": "稳定无显著变化",
    "neutral_or_small_change": "小幅变化",
}

SUPPORT_LABELS = {
    "strong": "强交叉支持",
    "moderate": "中等交叉支持",
    "limited": "有限交叉支持",
    "isolated": "孤立证据",
}

RELIABILITY_LABELS = {
    "high": "高可靠",
    "medium": "中等可靠",
    "low": "低可靠",
}


def decision_tier(score: Any) -> str:
    value = _float_or_none(score)
    if value is None:
        return "unknown"
    if value >= 80:
        return "strong_buy"
    if value >= 65:
        return "buy_candidate"
    if value >= 55:
        return "watch"
    if value >= 40:
        return "cautious"
    return "avoid"


def compare_scores(case: dict[str, Any], baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    base_score = _float_or_none(baseline.get("investment_score"))
    cand_score = _float_or_none(candidate.get("investment_score"))
    base_tier = decision_tier(base_score)
    cand_tier = decision_tier(cand_score)
    tier_delta = DECISION_ORDER.get(cand_tier, -1) - DECISION_ORDER.get(base_tier, -1)
    score_delta = None if base_score is None or cand_score is None else round(cand_score - base_score, 2)

    flags: list[str] = []
    expectation = case.get("expectation", "neutral")

    if baseline.get("error") or candidate.get("error"):
        flags.append("execution_error")
    if score_delta is not None and abs(score_delta) >= 8:
        flags.append("large_score_drift")
    if tier_delta != 0:
        flags.append("decision_tier_changed")

    min_score = case.get("min_candidate_score")
    max_score = case.get("max_candidate_score")
    if cand_score is not None and min_score is not None and cand_score < min_score:
        flags.append("below_candidate_floor")
    if cand_score is not None and max_score is not None and cand_score > max_score:
        flags.append("above_candidate_ceiling")
    _check_dim_boundaries(case, candidate, flags)

    if expectation == "quality_control":
        if tier_delta < 0:
            flags.append("quality_control_downgrade")
    elif expectation == "risk_control":
        if tier_delta > 0:
            flags.append("risk_control_upgrade")
    elif expectation == "speculative_watch":
        if cand_tier in {"buy_candidate", "strong_buy"}:
            flags.append("speculative_promoted_to_buy")

    if any(flag in REGRESSION_FLAGS for flag in flags):
        verdict = "possible_regression"
    elif flags:
        verdict = "review"
    else:
        verdict = "ok"

    explanation = explain_comparison(
        case=case,
        baseline=baseline,
        candidate=candidate,
        flags=flags,
        verdict=verdict,
        expectation=expectation,
        base_score=base_score,
        cand_score=cand_score,
        score_delta=score_delta,
        tier_delta=tier_delta,
    )

    return {
        "case": case.get("ticker") or case.get("name"),
        "group": case.get("group", "synthetic"),
        "role": case.get("role"),
        "expectation": expectation,
        "baseline": baseline,
        "candidate": candidate,
        "delta": {
            "investment_score": score_delta,
            "overall_score": _delta(baseline.get("overall_score"), candidate.get("overall_score")),
            "fundamental_score": _delta(baseline.get("fundamental_score"), candidate.get("fundamental_score")),
            "panel_consensus": _delta(baseline.get("panel_consensus"), candidate.get("panel_consensus")),
            "decision_tier": tier_delta,
        },
        "decision": {
            "baseline": base_tier,
            "candidate": cand_tier,
        },
        "flags": flags,
        "explanation": explanation,
        "verdict": verdict,
    }


def explain_comparison(
    *,
    case: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    flags: list[str],
    verdict: str,
    expectation: str,
    base_score: float | None,
    cand_score: float | None,
    score_delta: float | None,
    tier_delta: int,
) -> dict[str, Any]:
    metrics = _explanation_metrics(case, baseline, candidate, score_delta, tier_delta)
    category = _reason_category(case, flags, expectation, score_delta, tier_delta)
    confidence = _confidence_assessment(case, baseline, candidate, flags, verdict, expectation, metrics)
    return {
        "category": category,
        "label": REASON_LABELS.get(category, category),
        "rationale": _rationale(category, flags, expectation, base_score, cand_score, score_delta, tier_delta, metrics),
        "confidence": confidence,
        "metrics": metrics,
    }


def _reason_category(
    case: dict[str, Any],
    flags: list[str],
    expectation: str,
    score_delta: float | None,
    tier_delta: int,
) -> str:
    role = str(case.get("role", "")).lower()
    case_name = str(case.get("ticker") or case.get("name") or "").lower()
    flag_set = set(flags)
    if "execution_error" in flag_set:
        return "execution_failure"
    if any(
        (flag.endswith("_below_floor") or flag.endswith("_above_ceiling"))
        and flag.split("_", 1)[0].isdigit()
        for flag in flag_set
    ):
        return "field_contract_violation"
    if "quality_control_downgrade" in flag_set or (
        "below_candidate_floor" in flag_set and expectation == "quality_control"
    ):
        return "quality_control_possible_downgrade"
    if "risk_control_upgrade" in flag_set or (
        "above_candidate_ceiling" in flag_set and expectation == "risk_control"
    ):
        return "risk_control_suspicious_upgrade"
    if "speculative_promoted_to_buy" in flag_set or (
        "above_candidate_ceiling" in flag_set and expectation == "speculative_watch"
    ):
        return "speculative_promoted_to_buy"
    if expectation == "risk_control" and (tier_delta < 0 or (score_delta is not None and score_delta < 0)):
        return "risk_control_reasonable_tightening"
    if ("stage3" in case_name or "stage4" in case_name or "downtrend" in role) and tier_delta < 0:
        return "trend_guardrail_tightening"
    if expectation in {"data_gap", "negative_event"} or "missing" in case_name or "data" in role:
        return "data_quality_uncertain"
    if "large_score_drift" in flag_set:
        return "material_score_drift"
    if "decision_tier_changed" in flag_set:
        return "decision_tier_shift"
    if not flags and (score_delta is None or abs(score_delta) < 2):
        return "stable_no_material_change"
    return "neutral_or_small_change"


def _explanation_metrics(
    case: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    score_delta: float | None,
    tier_delta: int,
) -> dict[str, Any]:
    boundary_checks = _boundary_checks(case, candidate)
    violated = [item for item in boundary_checks if item["margin"] is not None and item["margin"] < 0]
    nearest = None
    if boundary_checks:
        margins = [abs(item["margin"]) for item in boundary_checks if item["margin"] is not None]
        nearest = round(min(margins), 2) if margins else None
    axis_deltas = _axis_deltas(baseline.get("axes") or {}, candidate.get("axes") or {})
    return {
        "abs_score_delta": None if score_delta is None else round(abs(score_delta), 2),
        "tier_delta": tier_delta,
        "boundary_checks": boundary_checks,
        "boundary_violations": violated,
        "nearest_boundary_distance": nearest,
        "threshold_sensitivity": _threshold_sensitivity(nearest),
        "top_axis_deltas": axis_deltas[:3],
    }


def _threshold_sensitivity(nearest_boundary_distance: float | None) -> dict[str, Any]:
    if nearest_boundary_distance is None:
        return {"level": "not_applicable", "stable_within": []}
    stable_within = [band for band in (1, 3, 5) if nearest_boundary_distance > band]
    if nearest_boundary_distance <= 1:
        level = "high"
    elif nearest_boundary_distance <= 3:
        level = "medium"
    elif nearest_boundary_distance <= 5:
        level = "low"
    else:
        level = "stable"
    return {
        "level": level,
        "stable_within": stable_within,
        "nearest_boundary_distance": nearest_boundary_distance,
    }


def _boundary_checks(case: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    cand_score = _float_or_none(candidate.get("investment_score"))
    min_score = case.get("min_candidate_score")
    max_score = case.get("max_candidate_score")
    if min_score is not None:
        checks.append(_boundary_item("investment_score", "min", cand_score, float(min_score)))
    if max_score is not None:
        checks.append(_boundary_item("investment_score", "max", cand_score, float(max_score)))
    dim_scores = candidate.get("dim_scores") or {}
    for dim, floor in (case.get("min_candidate_dim_scores") or {}).items():
        checks.append(_boundary_item(dim, "min", _float_or_none(dim_scores.get(dim)), float(floor)))
    for dim, ceiling in (case.get("max_candidate_dim_scores") or {}).items():
        checks.append(_boundary_item(dim, "max", _float_or_none(dim_scores.get(dim)), float(ceiling)))
    return checks


def _boundary_item(target: str, kind: str, value: float | None, limit: float) -> dict[str, Any]:
    if value is None:
        margin = None
        violated = True
    elif kind == "min":
        margin = round(value - limit, 2)
        violated = value < limit
    else:
        margin = round(limit - value, 2)
        violated = value > limit
    return {
        "target": target,
        "kind": kind,
        "value": None if value is None else round(value, 2),
        "limit": round(limit, 2),
        "margin": margin,
        "violated": violated,
    }


def _axis_deltas(baseline_axes: dict[str, Any], candidate_axes: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for axis in sorted(set(baseline_axes) | set(candidate_axes)):
        delta = _delta(_axis_value(baseline_axes.get(axis)), _axis_value(candidate_axes.get(axis)))
        if delta is not None and abs(delta) >= 0.5:
            rows.append({"axis": axis, "delta": delta})
    rows.sort(key=lambda item: abs(item["delta"]), reverse=True)
    return rows


def _axis_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("score", "value", "raw", "weighted"):
            if key in value:
                return value[key]
    return value


def _confidence_assessment(
    case: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    flags: list[str],
    verdict: str,
    expectation: str,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    score = 90
    factors: list[str] = []
    if baseline.get("error") or candidate.get("error"):
        score -= 60
        factors.append("分支执行或输出缺失")
    if _float_or_none(baseline.get("investment_score")) is None or _float_or_none(candidate.get("investment_score")) is None:
        score -= 35
        factors.append("缺少 investment_score")
    nearest = metrics.get("nearest_boundary_distance")
    if nearest is not None:
        if nearest <= 1:
            score -= 18
            factors.append("候选结果距离边界 <= 1 分")
        elif nearest <= 3:
            score -= 8
            factors.append("候选结果距离边界 <= 3 分")
    if expectation == "neutral":
        score -= 8
        factors.append("样本没有强预期方向")
    if expectation == "data_gap":
        score -= 10
        factors.append("样本用于数据缺口边界，天然需要人工复核")
    if verdict == "review" and not any(flag in REGRESSION_FLAGS for flag in flags):
        score -= 8
        factors.append("仅触发 review，未违反硬边界")
    if not flags:
        factors.append("未触发漂移或边界标记")
    score = max(0, min(100, score))
    if score >= 75:
        level = "high"
    elif score >= 50:
        level = "medium"
    else:
        level = "low"
    return {"level": level, "score": score, "factors": factors}


def _rationale(
    category: str,
    flags: list[str],
    expectation: str,
    base_score: float | None,
    cand_score: float | None,
    score_delta: float | None,
    tier_delta: int,
    metrics: dict[str, Any],
) -> str:
    score_text = f"{_fmt_num(base_score)} -> {_fmt_num(cand_score)}"
    if category == "execution_failure":
        return "至少一个分支执行失败或缺少输出，无法做中立比较。"
    if category == "field_contract_violation":
        return f"候选分支违反维度分数边界；分数 {score_text}，标记：{', '.join(flags)}。"
    if category == "quality_control_possible_downgrade":
        return f"质量控制样本被降到预设下限或更低档位；分数 {score_text}，需要确认是否误伤好公司。"
    if category == "risk_control_suspicious_upgrade":
        return f"风险控制样本被升到预设上限以上或更高档位；分数 {score_text}，需要确认是否放松风控。"
    if category == "speculative_promoted_to_buy":
        return f"投机观察样本进入买入档或越过上限；分数 {score_text}，需要检查是否把题材热度当成买点。"
    if category == "risk_control_reasonable_tightening":
        return f"风险样本分数/档位下调，方向符合风控预期；分数 {score_text}。"
    if category == "trend_guardrail_tightening":
        return f"Stage 3/4 或下跌趋势样本被降档，方向符合趋势护栏；分数 {score_text}。"
    if category == "data_quality_uncertain":
        return f"样本主要检验数据缺口或事件语义；分数 {score_text}，需结合字段契约看。"
    if category == "material_score_drift":
        return f"分数漂移达到阈值但未违反硬边界；分数 {score_text}，变化 {score_delta:+.1f}。"
    if category == "decision_tier_shift":
        return f"买卖档位变化但未违反样本边界；分数 {score_text}，档位变化 {tier_delta:+d}。"
    if category == "stable_no_material_change":
        return f"分数和档位基本稳定；分数 {score_text}。"
    return f"变化较小或无明确方向性边界；分数 {score_text}，预期类型 {expectation}。"


def _check_dim_boundaries(case: dict[str, Any], candidate: dict[str, Any], flags: list[str]) -> None:
    dim_scores = candidate.get("dim_scores") or {}
    for dim, floor in (case.get("min_candidate_dim_scores") or {}).items():
        score = _float_or_none(dim_scores.get(dim))
        if score is not None and score < float(floor):
            flags.append(f"{dim}_below_floor")
    for dim, ceiling in (case.get("max_candidate_dim_scores") or {}).items():
        score = _float_or_none(dim_scores.get(dim))
        if score is not None and score > float(ceiling):
            flags.append(f"{dim}_above_ceiling")


def _mode_raw(raw: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "medium":
        return raw
    dims = raw.get("dimensions") or {}
    return {
        **raw,
        "dimensions": {key: value for key, value in dims.items() if key in CORE_DIMS},
    }


def _selected_raw_cases(include_holdout: bool, extra_tickers: list[str]) -> list[dict[str, Any]]:
    groups = {"core"}
    if include_holdout:
        groups.add("holdout")
    cases = [case for case in RAW_CASES if case["group"] in groups]
    known = {case["ticker"] for case in cases}
    for ticker in extra_tickers:
        if ticker not in known:
            cases.append(
                {
                    "ticker": ticker,
                    "group": "extra",
                    "role": "user supplied cached raw_data case",
                    "expectation": "neutral",
                }
            )
            known.add(ticker)
    return cases


def build_payload(modes: list[str], raw_cases: list[dict[str, Any]], synthetic_cases: list[dict[str, Any]]) -> dict[str, Any]:
    raw_items = []
    missing = []
    for mode in modes:
        for case in raw_cases:
            ticker = case["ticker"]
            path = CACHE / ticker / "raw_data.json"
            if not path.exists():
                missing.append({"ticker": ticker, "mode": mode, "path": str(path)})
                continue
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw_items.append(
                {
                    "mode": mode,
                    "case": case,
                    "raw": _mode_raw(raw, mode),
                }
            )
        for case in SYNTHETIC_RAW_CASES:
            raw_items.append(
                {
                    "mode": mode,
                    "case": {key: value for key, value in case.items() if key != "raw"},
                    "raw": _mode_raw(case["raw"], mode),
                }
            )
    return {
        "raw_items": raw_items,
        "synthetic_cases": synthetic_cases,
        "missing": missing,
    }


def run_branch(ref: str, worktree: Path, payload: dict[str, Any], python_exe: str, timeout_sec: int) -> dict[str, Any]:
    payload_path = worktree / "_branch_score_payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "UZI_NO_UPDATE_CHECK": "1",
        }
    )
    try:
        proc = subprocess.run(
            [python_exe, "-c", BRANCH_RUNNER, str(worktree), str(payload_path), ref],
            cwd=str(worktree),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ref": ref,
            "error": f"branch_runner_timeout_after_{timeout_sec}s",
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "raw": [],
            "synthetic": [],
        }
    if proc.returncode != 0:
        return {
            "ref": ref,
            "error": "branch_runner_failed",
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "raw": [],
            "synthetic": [],
        }
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {
            "ref": ref,
            "error": f"invalid_json: {exc}",
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "raw": [],
            "synthetic": [],
        }


def add_worktree(ref: str, path: Path) -> None:
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(path), ref],
        cwd=str(ROOT),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def remove_worktree(path: Path) -> None:
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(path)],
        cwd=str(ROOT),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def compare_outputs(payload: dict[str, Any], baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_raw = {(row["mode"], row["case"]): row for row in baseline.get("raw", [])}
    candidate_raw = {(row["mode"], row["case"]): row for row in candidate.get("raw", [])}
    rows = []

    for item in payload["raw_items"]:
        key = (item["mode"], item["case"]["ticker"])
        case = {**item["case"], "name": f"{item['mode']} {item['case']['ticker']}"}
        base = baseline_raw.get(key, {"error": "missing_branch_output"})
        cand = candidate_raw.get(key, {"error": "missing_branch_output"})
        compared = compare_scores(case, base, cand)
        compared["mode"] = item["mode"]
        rows.append(compared)

    baseline_synthetic = {row["case"]: row for row in baseline.get("synthetic", [])}
    candidate_synthetic = {row["case"]: row for row in candidate.get("synthetic", [])}
    synthetic_rows = []
    for case in payload["synthetic_cases"]:
        base = baseline_synthetic.get(case["name"], {"error": "missing_branch_output"})
        cand = candidate_synthetic.get(case["name"], {"error": "missing_branch_output"})
        synthetic_rows.append(compare_scores(case, base, cand))

    all_rows = rows + synthetic_rows
    _attach_cross_support(all_rows)
    counts = {
        "ok": sum(1 for row in all_rows if row["verdict"] == "ok"),
        "review": sum(1 for row in all_rows if row["verdict"] == "review"),
        "possible_regression": sum(1 for row in all_rows if row["verdict"] == "possible_regression"),
    }
    reason_counts = _count_by(all_rows, lambda row: row["explanation"]["category"])
    confidence_counts = _count_by(all_rows, lambda row: row["explanation"]["confidence"]["level"])
    support_counts = _count_by(all_rows, lambda row: row["explanation"]["support"]["level"])
    reliability_counts = _count_by(all_rows, lambda row: row["explanation"]["reliability"]["level"])
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "baseline_ref": baseline.get("ref"),
        "candidate_ref": candidate.get("ref"),
        "baseline_error": baseline.get("error"),
        "candidate_error": candidate.get("error"),
        "missing_cache": payload.get("missing", []),
        "summary": counts,
        "reason_summary": reason_counts,
        "confidence_summary": confidence_counts,
        "support_summary": support_counts,
        "reliability_summary": reliability_counts,
        "raw_comparisons": rows,
        "synthetic_comparisons": synthetic_rows,
    }


def _attach_cross_support(rows: list[dict[str, Any]]) -> None:
    by_category: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        category = row["explanation"]["category"]
        by_category.setdefault(category, []).append(row)
    for row in rows:
        category = row["explanation"]["category"]
        peers = by_category.get(category, [])
        support = _cross_support_for(row, peers)
        row["explanation"]["support"] = support
        row["explanation"]["reliability"] = _reliability_for(row)


def _reliability_for(row: dict[str, Any]) -> dict[str, Any]:
    explanation = row["explanation"]
    confidence = explanation["confidence"]
    support = explanation["support"]
    sensitivity = (explanation["metrics"].get("threshold_sensitivity") or {}).get("level")
    score = int(confidence["score"])
    factors: list[str] = []

    support_penalty = {
        "strong": 0,
        "moderate": 5,
        "limited": 12,
        "isolated": 25,
    }.get(support["level"], 15)
    if support_penalty:
        score -= support_penalty
        factors.append(f"交叉支持为 {support['level']}")

    sensitivity_penalty = {
        "stable": 0,
        "low": 3,
        "medium": 6,
        "high": 12,
        "not_applicable": 0,
    }.get(str(sensitivity), 0)
    if sensitivity_penalty:
        score -= sensitivity_penalty
        factors.append(f"阈值敏感性为 {sensitivity}")

    if row["verdict"] == "possible_regression":
        factors.append("硬边界违反，仍需优先处理")
    elif row["verdict"] == "review":
        factors.append("review 结论需要人工复核")

    score = max(0, min(100, score))
    if score >= 75:
        level = "high"
    elif score >= 50:
        level = "medium"
    else:
        level = "low"
    if not factors:
        factors.append("单行置信度、交叉支持和阈值敏感性均稳定")
    return {
        "level": level,
        "label": RELIABILITY_LABELS[level],
        "score": score,
        "factors": factors,
    }


def _cross_support_for(row: dict[str, Any], peers: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_types = sorted({_evidence_type(peer) for peer in peers})
    groups = sorted({str(peer.get("group", "unknown")) for peer in peers})
    modes = sorted({str(peer.get("mode")) for peer in peers if peer.get("mode")})
    has_cached_raw = any(_evidence_type(peer) == "cached_raw" for peer in peers)
    has_synthetic = any(_evidence_type(peer).startswith("synthetic") for peer in peers)
    has_both_modes = {"lite", "medium"}.issubset(set(modes))
    count = len(peers)
    if count >= 4 and has_cached_raw and has_synthetic and has_both_modes:
        level = "strong"
        rationale = "同类归因同时出现在真实缓存、synthetic 样本和 lite/medium 模式中。"
    elif count >= 2 and ((has_cached_raw and has_both_modes) or (has_cached_raw and has_synthetic) or len(evidence_types) >= 2):
        level = "moderate"
        rationale = "同类归因有多条或多来源证据，但覆盖面还不完整。"
    elif count >= 2:
        level = "limited"
        rationale = "同类归因有重复样本支持，但来源类型较单一。"
    else:
        level = "isolated"
        rationale = "该归因目前只由单个样本支持，不能单独外推。"
    return {
        "level": level,
        "label": SUPPORT_LABELS[level],
        "rationale": rationale,
        "same_category_count": count,
        "evidence_types": evidence_types,
        "groups": groups,
        "modes": modes,
    }


def _evidence_type(row: dict[str, Any]) -> str:
    group = row.get("group")
    if group in {"core", "holdout", "extra"}:
        return "cached_raw"
    if group == "synthetic_raw":
        return "synthetic_raw"
    return "synthetic_feature"


def _count_by(rows: list[dict[str, Any]], key_fn: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(key_fn(row))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def write_outputs(result: dict[str, Any], label: str) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / f"{label}.json"
    md_path = OUT_DIR / f"{label}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# 分支评分对照 - {label}",
        "",
        f"基线分支：`{result['baseline_ref']}`",
        f"候选分支：`{result['candidate_ref']}`",
        f"生成时间：{result['generated_at']}",
        "",
        "## 汇总",
        "",
        f"- ok: {result['summary']['ok']}",
        f"- review: {result['summary']['review']}",
        f"- possible_regression: {result['summary']['possible_regression']}",
    ]
    lines.extend(["", "## 归因汇总", ""])
    for category, count in result.get("reason_summary", {}).items():
        lines.append(f"- {REASON_LABELS.get(category, category)} (`{category}`): {count}")
    lines.extend(["", "## 置信度汇总", ""])
    for level, count in result.get("confidence_summary", {}).items():
        lines.append(f"- {level}: {count}")
    lines.extend(["", "## 交叉支持汇总", ""])
    for level, count in result.get("support_summary", {}).items():
        lines.append(f"- {SUPPORT_LABELS.get(level, level)} (`{level}`): {count}")
    lines.extend(["", "## 可靠性汇总", ""])
    for level, count in result.get("reliability_summary", {}).items():
        lines.append(f"- {RELIABILITY_LABELS.get(level, level)} (`{level}`): {count}")
    if result.get("missing_cache"):
        lines.extend(["", "## 缺失缓存", ""])
        for item in result["missing_cache"]:
            lines.append(f"- {item['mode']} {item['ticker']}: `{item['path']}`")

    lines.extend(
        [
            "",
            "## 缓存 Raw Data",
            "",
            "| 判定 | 归因 | 置信度 | 交叉支持 | 可靠性 | 模式 | 样本 | 基线 | 候选 | 变化 | 基线档位 | 候选档位 | 边界余量 | 标记 |",
            "|---|---|---|---|---|---|---|---:|---:|---:|---|---|---:|---|",
        ]
    )
    for row in result["raw_comparisons"]:
        lines.append(_format_md_row(row))

    lines.extend(
        [
            "",
            "## Synthetic 对抗样本",
            "",
            "| 判定 | 归因 | 置信度 | 交叉支持 | 可靠性 | 样本 | 基线 | 候选 | 变化 | 基线档位 | 候选档位 | 边界余量 | 标记 |",
            "|---|---|---|---|---|---|---:|---:|---:|---|---|---:|---|",
        ]
    )
    for row in result["synthetic_comparisons"]:
        lines.append(_format_md_row(row, include_mode=False))

    lines.extend(["", "## 说明", ""])
    lines.append("- `review` 表示分数或档位变化值得检查，但不自动等同于回退。")
    lines.append("- `possible_regression` 表示候选分支违反了样本特定决策边界。")
    lines.append("- `归因` 是稳定枚举，优先按执行失败、字段契约、硬边界、样本预期和漂移强度分类。")
    lines.append("- `置信度` 不是预测胜率，而是本次判定的证据完整度；执行错误、分数缺失、贴近边界、弱预期样本会降低置信度。")
    lines.append("- `交叉支持` 衡量同类归因是否被不同样本来源和 lite/medium 模式共同支持；它不改变判定，只用于识别过拟合风险。")
    lines.append("- `可靠性` 综合置信度、交叉支持和阈值敏感性；它不改变判定，只决定结论能说多满。")
    lines.append("- `边界余量` 为候选结果距离最近预设边界的分数；负数表示越界，越接近 0 越需要人工复核。")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _format_md_row(row: dict[str, Any], include_mode: bool = True) -> str:
    baseline = row["baseline"]
    candidate = row["candidate"]
    explanation = row["explanation"]
    confidence = explanation["confidence"]
    support = explanation["support"]
    reliability = explanation["reliability"]
    cells = [
        row["verdict"],
        explanation["label"],
        f"{confidence['level']}({confidence['score']})",
        support["label"],
        f"{reliability['level']}({reliability['score']})",
    ]
    if include_mode:
        cells.append(row.get("mode", ""))
    cells.extend(
        [
            row["case"],
            _fmt_num(baseline.get("investment_score")),
            _fmt_num(candidate.get("investment_score")),
            _fmt_num(row["delta"].get("investment_score")),
            row["decision"]["baseline"],
            row["decision"]["candidate"],
            _fmt_num(explanation["metrics"].get("nearest_boundary_distance")),
            ", ".join(row["flags"]) or "-",
        ]
    )
    return "| " + " | ".join(cells) + " |"


def _fmt_num(value: Any) -> str:
    number = _float_or_none(value)
    if number is None:
        return "-"
    return f"{number:.1f}"


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _delta(a: Any, b: Any) -> float | None:
    fa = _float_or_none(a)
    fb = _float_or_none(b)
    if fa is None or fb is None:
        return None
    return round(fb - fa, 2)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two git refs with the same cached raw_data and pure scoring functions."
    )
    parser.add_argument("--baseline", default="codex/windows-local-stable")
    parser.add_argument("--candidate", default="codex/scoring-validation-guardrails")
    parser.add_argument("--mode", choices=("lite", "medium", "both"), default="both")
    parser.add_argument("--include-holdout", action="store_true", default=True)
    parser.add_argument("--no-holdout", dest="include_holdout", action="store_false")
    parser.add_argument("--extra-ticker", action="append", default=[])
    parser.add_argument("--label", default=time.strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--runner-timeout", type=int, default=300)
    parser.add_argument("--keep-worktrees", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    modes = ["lite", "medium"] if args.mode == "both" else [args.mode]
    raw_cases = _selected_raw_cases(args.include_holdout, args.extra_ticker)
    payload = build_payload(modes, raw_cases, SYNTHETIC_CASES)

    with tempfile.TemporaryDirectory(prefix="uzi-branch-score-") as td:
        temp_root = Path(td)
        baseline_tree = temp_root / "baseline"
        candidate_tree = temp_root / "candidate"
        try:
            add_worktree(args.baseline, baseline_tree)
            add_worktree(args.candidate, candidate_tree)
            baseline = run_branch(args.baseline, baseline_tree, payload, args.python, args.runner_timeout)
            candidate = run_branch(args.candidate, candidate_tree, payload, args.python, args.runner_timeout)
        finally:
            if not args.keep_worktrees:
                remove_worktree(baseline_tree)
                remove_worktree(candidate_tree)

        result = compare_outputs(payload, baseline, candidate)
        if not args.no_write:
            json_path, md_path = write_outputs(result, args.label)
            print(f"wrote {json_path}")
            print(f"wrote {md_path}")

        print(json.dumps(result["summary"], ensure_ascii=False))
        for row in result["raw_comparisons"] + result["synthetic_comparisons"]:
            if row["verdict"] != "ok":
                print(
                    f"{row['verdict']}: {row['case']} "
                    f"{_fmt_num(row['baseline'].get('investment_score'))} -> "
                    f"{_fmt_num(row['candidate'].get('investment_score'))} "
                    f"flags={','.join(row['flags'])}"
                )

        return 1 if result["summary"]["possible_regression"] else 0


BRANCH_RUNNER = r"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

repo = Path(sys.argv[1])
payload_path = Path(sys.argv[2])
ref = sys.argv[3]
scripts = repo / "skills" / "deep-analysis" / "scripts"
sys.path.insert(0, str(scripts))


def quiet(fn, *args):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        return fn(*args)


def compact_synthesis(syn, panel=None, dims=None):
    scorecard = syn.get("investment_scorecard") or {}
    diagnostics = scorecard.get("diagnostics") or {}
    return {
        "overall_score": syn.get("overall_score"),
        "legacy_overall_score": syn.get("legacy_overall_score"),
        "investment_score": syn.get("investment_score"),
        "investment_rating": syn.get("investment_rating"),
        "verdict_label": syn.get("verdict_label"),
        "fundamental_score": syn.get("fundamental_score"),
        "panel_consensus": syn.get("panel_consensus"),
        "axes": scorecard.get("axes") or {},
        "weights": scorecard.get("weights") or {},
        "guardrails": diagnostics.get("guardrails") or {},
        "polarize_k": (panel or {}).get("consensus_formula", {}).get("polarize_k"),
        "dim_scores": {
            key: value.get("score")
            for key, value in ((dims or {}).get("dimensions") or {}).items()
        },
    }


def compact_scorecard(card):
    diagnostics = card.get("diagnostics") or {}
    return {
        "overall_score": None,
        "investment_score": card.get("score"),
        "investment_rating": card.get("rating"),
        "verdict_label": card.get("rating"),
        "fundamental_score": None,
        "panel_consensus": None,
        "axes": card.get("axes") or {},
        "weights": card.get("weights") or {},
        "guardrails": diagnostics.get("guardrails") or {},
    }


payload = json.loads(payload_path.read_text(encoding="utf-8"))
try:
    from lib.pipeline.score_fns import (
        compute_investment_score,
        generate_panel,
        generate_synthesis,
        score_dimensions,
    )
except Exception as exc:
    print(json.dumps({"ref": ref, "error": f"import_failed: {type(exc).__name__}: {exc}", "raw": [], "synthetic": []}))
    raise SystemExit(0)

raw_rows = []
for item in payload.get("raw_items", []):
    case = item["case"]["ticker"]
    mode = item["mode"]
    old_depth = os.environ.get("UZI_DEPTH")
    os.environ["UZI_DEPTH"] = mode
    try:
        dims = quiet(score_dimensions, item["raw"])
        panel = quiet(generate_panel, dims, item["raw"])
        syn = quiet(generate_synthesis, item["raw"], dims, panel)
        row = {"case": case, "mode": mode, **compact_synthesis(syn, panel, dims)}
    except Exception as exc:
        row = {"case": case, "mode": mode, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if old_depth is None:
            os.environ.pop("UZI_DEPTH", None)
        else:
            os.environ["UZI_DEPTH"] = old_depth
    raw_rows.append(row)

synthetic_rows = []
for case in payload.get("synthetic_cases", []):
    try:
        card = quiet(compute_investment_score, case["features"])
        row = {"case": case["name"], **compact_scorecard(card)}
    except Exception as exc:
        row = {"case": case["name"], "error": f"{type(exc).__name__}: {exc}"}
    synthetic_rows.append(row)

print(json.dumps({"ref": ref, "raw": raw_rows, "synthetic": synthetic_rows}, ensure_ascii=False))
"""


if __name__ == "__main__":
    raise SystemExit(main())
