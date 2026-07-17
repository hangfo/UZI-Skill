import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def test_investment_score_rewards_quality_a_share_without_ignoring_valuation():
    from lib.pipeline.score_fns import compute_investment_score

    scorecard = compute_investment_score({
        "market": "A",
        "market_cap_yi": 14819,
        "roe_5y_avg": 25,
        "roe_5y_min": 20,
        "net_margin": 52,
        "gross_margin": 90,
        "revenue_growth_3y_cagr": 12,
        "net_profit_growth_latest": 15,
        "pe": 18,
        "pb": 6,
        "pe_quantile_5y": 35,
        "stage_num": 4,
        "ytd_return": -15,
        "volatility_1y": 28,
        "max_drawdown_1y": -25,
        "is_safe": True,
    })

    assert 55 <= scorecard["score"] <= 60
    assert scorecard["axes"]["quality"] >= 80
    assert scorecard["axes"]["risk_control"] >= 50
    assert scorecard["diagnostics"]["guardrails"]["falling_trend_cap"] is True


def test_investment_score_caps_expensive_unprofitable_us_growth():
    from lib.pipeline.score_fns import compute_investment_score

    scorecard = compute_investment_score({
        "market": "US",
        "market_cap_yi": 1900,
        "roe_5y_avg": 0,
        "net_margin": -1,
        "gross_margin": 75,
        "revenue_growth_3y_cagr": 30,
        "net_profit_growth_latest": 0,
        "pe": 0,
        "pb": 42,
        "stage_num": 2,
        "ytd_return": 49,
        "volatility_1y": 55,
        "max_drawdown_1y": -45,
        "has_positive_catalyst": True,
        "buy_rating_pct": 80,
        "is_safe": True,
    })

    assert scorecard["score"] < 65
    assert scorecard["axes"]["growth"] >= 70
    assert scorecard["axes"]["valuation"] < 45
    assert scorecard["diagnostics"]["guardrails"]["buyback_distorted_pb"] is False
    assert scorecard["axes"]["risk_control"] < 50


def test_investment_score_handles_quality_us_with_valuation_cap():
    from lib.pipeline.score_fns import compute_investment_score

    scorecard = compute_investment_score({
        "market": "US",
        "market_cap_yi": 42000,
        "roe_5y_avg": 70,
        "net_margin": 55,
        "gross_margin": 75,
        "revenue_growth_3y_cagr": 18,
        "net_profit_growth_latest": 20,
        "pe": 32,
        "pb": 24,
        "stage_num": 2,
        "ytd_return": 7,
        "volatility_1y": 24,
        "max_drawdown_1y": -20,
        "is_safe": True,
    })

    assert 55 <= scorecard["score"] <= 70
    assert scorecard["axes"]["quality"] >= 80
    assert scorecard["axes"]["valuation"] >= 40
    assert scorecard["diagnostics"]["guardrails"]["buyback_distorted_pb"] is True


def test_investment_score_handles_hk_platform_without_a_share_fields():
    from lib.pipeline.score_fns import compute_investment_score

    scorecard = compute_investment_score({
        "market": "HK",
        "market_cap_yi": 33266,
        "roe_5y_avg": 18,
        "net_margin": 24,
        "gross_margin": 48,
        "revenue_growth_3y_cagr": 10,
        "net_profit_growth_latest": 20,
        "pe": 18,
        "pb": 3,
        "stage_num": 4,
        "ytd_return": -30,
        "volatility_1y": 30,
        "max_drawdown_1y": -35,
        "is_safe": True,
    })

    assert 50 <= scorecard["score"] <= 70
    assert scorecard["axes"]["quality"] >= 70
    assert scorecard["axes"]["growth"] < 55
    assert scorecard["diagnostics"]["guardrails"]["falling_trend_cap"] is True


def test_investment_score_keeps_extreme_smallcap_momentum_risk_capped():
    from lib.pipeline.score_fns import compute_investment_score

    scorecard = compute_investment_score({
        "market": "US",
        "market_cap_yi": 47,
        "roe_5y_avg": 0,
        "net_margin": -15,
        "gross_margin": 20,
        "revenue_growth_3y_cagr": -14,
        "net_profit_growth_latest": -30,
        "pe": 0,
        "pb": 14,
        "stage_num": 2,
        "ytd_return": 330,
        "volatility_1y": 139,
        "max_drawdown_1y": -51,
        "ai_chokepoint_score": 85,
        "has_positive_catalyst": True,
        "is_safe": True,
    })

    assert scorecard["score"] <= 58
    assert scorecard["axes"]["catalyst"] >= 70
    assert scorecard["axes"]["risk_control"] < 30
    assert scorecard["diagnostics"]["guardrails"]["speculative_quality_risk_cap"] is True


def test_synthesis_exports_investment_score_without_blending_overall():
    from lib.pipeline.score_fns import generate_synthesis

    raw = {
        "ticker": "300750.SZ",
        "market": "A",
        "dimensions": {
            "0_basic": {"data": {
                "code": "300750.SZ",
                "name": "宁德时代",
                "industry": "电池",
                "price": 392.36,
                "market_cap": "18153.0亿",
                "market_cap_raw": 1_815_300_000_000,
                "pe_ttm": 23,
                "pb": 5.5,
            }},
            "1_financials": {"data": {
                "roe_history": [21, 22, 24, 25, 26],
                "revenue_history": [100, 140, 210, 320],
                "net_profit_history": [12, 20, 35, 58],
                "net_margin": 18,
                "gross_margin": 36,
                "financial_health": {"debt_ratio": 38, "fcf_margin": 8},
            }},
            "2_kline": {"data": {
                "stage": "Stage 2 上升",
                "ma_align": "多头排列",
                "kline_stats": {"ytd_return": "+62.1%", "volatility": "35.0%", "max_drawdown": "-22.0%"},
            }},
            "10_valuation": {"data": {"pe_quantile": "5 年 25 分位", "pe": 23, "pb": 5.5}},
            "11_governance": {"data": {}},
            "15_events": {"data": {"event_timeline": ["储能订单增长", "新品发布"]}},
            "16_lhb": {"data": {}},
        },
    }
    dims_scored = {
        "ticker": "300750.SZ",
        "fundamental_score": 62.0,
        "dimensions": {
            "1_financials": {"score": 7, "weight": 5, "label": "ok"},
            "2_kline": {"score": 8, "weight": 4, "label": "ok"},
            "10_valuation": {"score": 8, "weight": 5, "label": "ok"},
        },
    }
    panel = {
        "panel_consensus": 58.0,
        "signal_distribution": {"bullish": 4, "neutral": 3, "bearish": 3, "skip": 0},
        "investors": [
            {"investor_id": "a", "name": "Bull", "group": "A", "score": 80, "signal": "bullish", "headline": "看多", "reasoning": "", "pass": [], "fail": []},
            {"investor_id": "b", "name": "Bear", "group": "B", "score": 30, "signal": "bearish", "headline": "看空", "reasoning": "", "pass": [], "fail": []},
        ],
        "school_scores": {},
    }

    syn = generate_synthesis(raw, dims_scored, panel)

    assert syn["investment_score"] >= 70
    assert syn["overall_score"] == syn["legacy_overall_score"]
    assert "买入评分" in syn["verdict_detail"]
    assert syn["investment_decision"]["quadrant"] in {
        "core_watch", "tactical_only", "quality_watch", "avoid",
    }
    assert syn["investment_scorecard"]["axes"]["quality"] >= 70


def test_buy_score_orders_aapl_above_falling_a_h_quality_names():
    from lib.pipeline.score_fns import compute_investment_score

    maotai = compute_investment_score({
        "market": "A", "market_cap_yi": 14819, "roe_5y_avg": 32.6, "roe_5y_min": 29.9,
        "net_margin": 47.8, "gross_margin": 65.8, "revenue_growth_3y_cagr": 10.5,
        "net_profit_growth_latest": -4.5, "pe": 17.9, "pb": 6.4, "pe_quantile_5y": 5,
        "stage_num": 4, "ytd_return": -14.9, "volatility_1y": 20.1, "max_drawdown_1y": -23.1,
        "is_safe": True,
    })
    tencent = compute_investment_score({
        "market": "HK", "market_cap_yi": 33266, "roe_5y_avg": 22.5, "roe_5y_min": 15.1,
        "net_margin": 29.9, "gross_margin": 56.2, "revenue_growth_3y_cagr": 10.7,
        "net_profit_growth_latest": 15.9, "pe": 14.9, "pb": 3.1,
        "stage_num": 4, "ytd_return": -30.2, "volatility_1y": 30.2, "max_drawdown_1y": -38.5,
        "is_safe": True,
    })
    apple = compute_investment_score({
        "market": "US", "market_cap_yi": 42499, "roe_5y_avg": 141.5, "roe_5y_min": 141.5,
        "net_margin": 26.9, "gross_margin": 44.9, "revenue_growth_3y_cagr": 1.8,
        "net_profit_growth_latest": 19.5, "pe": 35.1, "pb": 39.9,
        "stage_num": 2, "ytd_return": 7.0, "volatility_1y": 23.8, "max_drawdown_1y": -13.8,
        "is_safe": True,
    })

    assert apple["score"] > maotai["score"]
    assert apple["score"] > tencent["score"]
    # Distinct axis profiles may legitimately round to the same integer score;
    # assert the economic distinction instead of overfitting to rounding noise.
    assert maotai["axes"]["quality"] != tencent["axes"]["quality"]
    assert maotai["axes"]["valuation"] != tencent["axes"]["valuation"]
    assert maotai["diagnostics"]["guardrails"]["falling_trend_cap"] is True
    assert tencent["diagnostics"]["guardrails"]["falling_trend_cap"] is True
    assert apple["diagnostics"]["guardrails"]["buyback_distorted_pb"] is True
