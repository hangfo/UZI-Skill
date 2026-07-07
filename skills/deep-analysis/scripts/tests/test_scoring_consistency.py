"""Scoring consistency test suite — Task #4 (v4.0)

Covers four risk categories identified in SCORING_ANALYSIS.md:
1. Monotonicity — axes must move in the right direction as inputs improve
2. Guardrail constraints — junk stocks must not exceed 45; caps must fire
3. Holdout ordering basket — AAPL > Maotai > Tencent > MSTR (buy_score)
4. Field-contract smoke tests — dim_15 / rev_growth alias / weights

All tests are pure-function / network-free.  They call compute_investment_score
(five-axis buyer score) and score_dimensions (22-dim fundamental score) with
synthetic feature/raw dicts.  No cache, no API, no disk I/O.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_features(**overrides) -> dict:
    """Return a 'decent quality' base features dict, override as needed."""
    base = {
        # valuation
        "pe": 20.0, "pb": 3.0, "pe_quantile_5y": 50.0, "dividend_yield": 1.0,
        # profitability
        "roe_latest": 15.0, "roe_5y_avg": 15.0, "roe_5y_min": 10.0,
        "net_margin": 15.0, "gross_margin": 40.0, "fcf_margin": 5.0,
        # growth
        "revenue_growth_3y_cagr": 15.0, "revenue_growth_latest": 12.0,
        "net_profit_growth_latest": 15.0,
        # P0-A alias bridge (should be populated by extract_features wrapper)
        "rev_growth_3y": 15.0, "rev_growth_yoy": 12.0,
        # risk
        "debt_ratio": 30.0, "volatility_1y": 30.0, "max_drawdown_1y": -15.0,
        "ytd_return": 10.0,
        # technical
        "stage_num": 2, "stage": "Stage 2",
        # moat / other
        "moat_total": 20.0, "market_cap_yi": 5000.0, "market": "US",
        # analyst
        "buy_rating_pct": 60.0, "upside_to_target": 15.0,
        # sentiment
        "sentiment_heat": 30.0, "ai_chokepoint_score": 0.0,
        "peg": 1.3,
        "lhb_30d_count": 0,
    }
    base.update(overrides)
    return base


def _make_raw(dims_override: dict | None = None, ticker: str = "TEST") -> dict:
    """Return a minimal raw dict suitable for score_dimensions()."""
    dims_override = dims_override or {}

    def _dim(data: dict) -> dict:
        return {"data": data}

    base_dims: dict[str, dict] = {
        "0_basic":    _dim({"name": ticker, "industry": "Technology", "price": "100"}),
        "1_financials": _dim({
            "roe": 15.0, "roe_history": [12, 14, 15],
            "net_margin": 15.0,
            "revenue_history": [800, 900, 1000, 1150],
            "financial_health": {"debt_ratio": 30.0},
        }),
        "2_kline":    _dim({"stage": "Stage 2 · Markup", "ma_align": "多头排列",
                             "kline_stats": {"max_drawdown": "-15%", "ytd_return": "+12%"}}),
        "3_macro":    _dim({}),
        "4_peers":    _dim({}),
        "5_chain":    _dim({}),
        "6_research": _dim({"report_count": 10, "rating_distribution": {"买入": 6}}),
        "7_industry": _dim({}),
        "8_materials": _dim({}),
        "9_futures":  _dim({}),
        "10_valuation": _dim({"pe": "20", "pe_quantile": "50分位", "industry_pe": "25"}),
        "11_governance": _dim({"pledge": [], "insider_trades_1y": True}),
        "12_capital_flow": _dim({"main_fund_flow_20d": [], "unlock_schedule": []}),
        "13_policy":  _dim({}),
        "14_moat":    _dim({}),
        "15_events":  _dim({}),
        "16_lhb":     _dim({"lhb_count_30d": 0, "matched_youzi": []}),
        "17_sentiment": _dim({"hot_rank": {"rank_history": []}}),
        "18_trap":    _dim({}),
        "19_contests": _dim({"summary": {"xueqiu_cubes_total": 0, "high_return_cubes": 0}}),
    }
    for k, v in dims_override.items():
        base_dims[k] = v
    return {"ticker": ticker, "dimensions": base_dims}


# ─── import the functions under test ─────────────────────────────────────────

from lib.pipeline.score_fns import compute_investment_score, score_dimensions  # noqa: E402


# ═══════════════════════════════════════════════════════════════
# 1 · MONOTONICITY TESTS
# ═══════════════════════════════════════════════════════════════

def test_roe_monotonicity():
    """Quality axis must increase strictly as ROE increases (5→10→15→20→25→30%)."""
    roe_levels = [5, 10, 15, 20, 25, 30]
    prev_quality = None
    for roe in roe_levels:
        f = _make_features(roe_5y_avg=roe, roe_latest=roe, roe_5y_min=max(0, roe - 3))
        result = compute_investment_score(f)
        quality = result["axes"]["quality"]
        if prev_quality is not None:
            assert quality >= prev_quality, (
                f"quality did not increase when ROE went from {roe_levels[roe_levels.index(roe)-1]}% "
                f"to {roe}%: {prev_quality:.1f} → {quality:.1f}"
            )
        prev_quality = quality


def test_pe_quantile_monotonicity():
    """Valuation axis must decrease (not improve) as PE quantile rises (10→30→50→70→90)."""
    pe_quantile_levels = [10, 30, 50, 70, 90]
    prev_valuation = None
    for pe_q in pe_quantile_levels:
        f = _make_features(pe_quantile_5y=float(pe_q), pe=20.0)
        result = compute_investment_score(f)
        valuation = result["axes"]["valuation"]
        if prev_valuation is not None:
            assert valuation <= prev_valuation, (
                f"valuation did not decrease when PE quantile went from "
                f"{pe_quantile_levels[pe_quantile_levels.index(pe_q)-1]} "
                f"to {pe_q}: {prev_valuation:.1f} → {valuation:.1f}"
            )
        prev_valuation = valuation


def test_rev_growth_monotonicity():
    """Buy score must increase as revenue growth goes from 0%→10%→20%→35% (all else equal)."""
    growth_levels = [0, 10, 20, 35]
    prev_score = None
    for g in growth_levels:
        f = _make_features(
            revenue_growth_3y_cagr=float(g),
            revenue_growth_latest=float(g),
            rev_growth_3y=float(g),
            rev_growth_yoy=float(g),
        )
        result = compute_investment_score(f)
        score = result["score"]
        if prev_score is not None:
            assert score >= prev_score, (
                f"buy_score did not increase as rev_growth went {growth_levels[growth_levels.index(g)-1]}→{g}%: "
                f"{prev_score:.1f} → {score:.1f}"
            )
        prev_score = score


def test_debt_ratio_risk_monotonicity():
    """Risk axis must decrease as debt_ratio increases (20→40→60→80%)."""
    debt_levels = [20, 40, 60, 80]
    prev_risk = None
    for d in debt_levels:
        f = _make_features(debt_ratio=float(d))
        result = compute_investment_score(f)
        risk = result["axes"]["risk_control"]
        if prev_risk is not None:
            assert risk <= prev_risk, (
                f"risk_control did not decrease as debt_ratio went "
                f"from {debt_levels[debt_levels.index(d)-1]} to {d}%: "
                f"{prev_risk:.1f} → {risk:.1f}"
            )
        prev_risk = risk


# ═══════════════════════════════════════════════════════════════
# 2 · GUARDRAIL CONSTRAINT TESTS
# ═══════════════════════════════════════════════════════════════

def test_no_junk_above_45():
    """Abysmally bad fundamentals + extreme speculation must never exceed 45."""
    junk = _make_features(
        roe_5y_avg=-5.0, roe_latest=-5.0, roe_5y_min=-15.0,
        net_margin=-20.0, gross_margin=10.0, fcf_margin=-15.0,
        revenue_growth_3y_cagr=5.0, net_profit_growth_latest=-30.0,
        debt_ratio=75.0, volatility_1y=130.0, max_drawdown_1y=-65.0,
        ytd_return=350.0,   # pump
        stage_num=4, pe=150.0, pb=25.0, pe_quantile_5y=95.0,
        moat_total=0.0, market_cap_yi=20.0,  # tiny mcap
        is_safe=False,
    )
    result = compute_investment_score(junk)
    assert result["score"] <= 45, (
        f"Junk stock with terrible fundamentals scored {result['score']:.1f} > 45 — guardrail failed"
    )


def test_stage3_quality_floor_blocked():
    """High-quality Stage 3 stock must NOT receive quality_floor boost (≥64 min)."""
    # Build a stock that WOULD get quality_floor in Stage 2 (quality>=85, risk>=55, val>=45)
    stage3_high_quality = _make_features(
        roe_5y_avg=28.0, roe_latest=28.0, roe_5y_min=18.0,
        net_margin=30.0, gross_margin=65.0, fcf_margin=15.0,
        moat_total=30.0,
        debt_ratio=15.0, volatility_1y=25.0, max_drawdown_1y=-20.0,
        pe=22.0, pb=5.0, pe_quantile_5y=45.0,
        # Stage 3 + price confirmation (ytd negative confirms distribution)
        stage_num=3, ytd_return=-15.0,
    )
    result = compute_investment_score(stage3_high_quality)
    # Guardrails: falling_trend_cap must fire, preventing quality_floor
    diag = result["diagnostics"]["guardrails"]
    assert diag["falling_trend_cap"], (
        "Stage 3 with ytd=-15% must trigger falling_trend_cap"
    )
    # The score must not be boosted to quality_floor territory
    assert result["score"] < 64, (
        f"Stage 3 high-quality stock got quality_floor boost: score={result['score']:.1f} ≥ 64 — cap failed"
    )


def test_stage4_cap_still_fires():
    """Stage 4 falling trend cap must still work (regression guard for P0-C change)."""
    stage4 = _make_features(
        stage_num=4, ytd_return=-20.0, max_drawdown_1y=-30.0,
        roe_5y_avg=25.0, net_margin=20.0, moat_total=28.0,
        pe_quantile_5y=40.0, debt_ratio=20.0, volatility_1y=30.0,
    )
    result = compute_investment_score(stage4)
    diag = result["diagnostics"]["guardrails"]
    assert diag["falling_trend_cap"], "Stage 4 must still trigger falling_trend_cap"
    assert result["score"] <= 59, (
        f"Stage 4 capped score should be ≤59, got {result['score']:.1f}"
    )


# ═══════════════════════════════════════════════════════════════
# 3 · HOLDOUT ORDERING BASKET
# ═══════════════════════════════════════════════════════════════

# Approximate feature profiles (synthetic, network-free)
_AAPL = _make_features(
    # Profitability
    roe_5y_avg=35.0, roe_latest=35.0, roe_5y_min=25.0,
    net_margin=25.0, gross_margin=45.0, fcf_margin=22.0,
    # Growth (moderate)
    revenue_growth_3y_cagr=8.0, revenue_growth_latest=5.0,
    rev_growth_3y=8.0, rev_growth_yoy=5.0,
    net_profit_growth_latest=10.0,
    # Valuation
    pe=30.0, pb=40.0, pe_quantile_5y=65.0, dividend_yield=0.5,
    # Risk (large cap, low debt)
    debt_ratio=40.0, volatility_1y=25.0, max_drawdown_1y=-20.0,
    ytd_return=15.0, stage_num=2,
    moat_total=32.0, market_cap_yi=200_000.0, market="US",
    buy_rating_pct=70.0, upside_to_target=10.0,
    is_safe=True,
)

_MAOTAI = _make_features(
    # Profitability (Chinese premium spirits — near-perfect fundamentals)
    roe_5y_avg=30.0, roe_latest=32.0, roe_5y_min=22.0,
    net_margin=55.0, gross_margin=92.0, fcf_margin=45.0,
    # Growth (mature, slower)
    revenue_growth_3y_cagr=15.0, revenue_growth_latest=18.0,
    rev_growth_3y=15.0, rev_growth_yoy=18.0,
    net_profit_growth_latest=18.0,
    # Valuation
    pe=28.0, pb=10.0, pe_quantile_5y=50.0, dividend_yield=2.5,
    # Risk
    debt_ratio=15.0, volatility_1y=20.0, max_drawdown_1y=-15.0,
    ytd_return=5.0, stage_num=2,
    moat_total=36.0, market_cap_yi=20_000.0, market="A",
    buy_rating_pct=75.0, upside_to_target=15.0,
    is_safe=True,
)

_TENCENT = _make_features(
    # Profitability
    roe_5y_avg=20.0, roe_latest=22.0, roe_5y_min=12.0,
    net_margin=25.0, gross_margin=50.0, fcf_margin=18.0,
    # Growth
    revenue_growth_3y_cagr=12.0, revenue_growth_latest=10.0,
    rev_growth_3y=12.0, rev_growth_yoy=10.0,
    net_profit_growth_latest=12.0,
    # Valuation
    pe=20.0, pb=3.5, pe_quantile_5y=45.0, dividend_yield=1.0,
    # Risk
    debt_ratio=25.0, volatility_1y=28.0, max_drawdown_1y=-20.0,
    ytd_return=0.0, stage_num=2,
    moat_total=30.0, market_cap_yi=30_000.0, market="HK",
    buy_rating_pct=70.0, upside_to_target=20.0,
    is_safe=True,
)

_MSTR = _make_features(
    # Profitability — poor, loss-making ex-Bitcoin
    roe_5y_avg=-5.0, roe_latest=0.0, roe_5y_min=-20.0,
    net_margin=-5.0, gross_margin=70.0, fcf_margin=-10.0,
    # Growth — software revenue flat
    revenue_growth_3y_cagr=2.0, revenue_growth_latest=0.0,
    rev_growth_3y=2.0, rev_growth_yoy=0.0,
    net_profit_growth_latest=-50.0,
    # Valuation — extreme premium on BTC bet
    pe=0.0, pb=3.0, pe_quantile_5y=90.0, dividend_yield=0.0,
    # Risk — high volatility, big drawdown, tiny float
    debt_ratio=65.0, volatility_1y=150.0, max_drawdown_1y=-70.0,
    ytd_return=200.0, stage_num=2,
    moat_total=5.0, market_cap_yi=8_000.0, market="US",
    buy_rating_pct=30.0, upside_to_target=0.0,
    ai_chokepoint_score=0.0,
)


def test_maotai_score_beats_mstr():
    """Maotai (high-quality profit machine) must score higher than MSTR (BTC leveraged bet)."""
    maotai = compute_investment_score(_MAOTAI)["score"]
    mstr   = compute_investment_score(_MSTR)["score"]
    assert maotai > mstr, (
        f"Maotai ({maotai:.1f}) should outscore MSTR ({mstr:.1f}) on buy_score"
    )


def test_tencent_score_beats_mstr():
    """Tencent (profitable internet platform) must outscore MSTR."""
    tencent = compute_investment_score(_TENCENT)["score"]
    mstr    = compute_investment_score(_MSTR)["score"]
    assert tencent > mstr, (
        f"Tencent ({tencent:.1f}) should outscore MSTR ({mstr:.1f})"
    )


def test_holdout_high_quality_outperforms_speculative():
    """Maotai (quality) must outscore a pure-speculation profile."""
    pure_speculation = _make_features(
        roe_5y_avg=0.0, net_margin=-10.0, debt_ratio=70.0,
        volatility_1y=200.0, max_drawdown_1y=-80.0, ytd_return=500.0,
        stage_num=4, ai_chokepoint_score=90.0,   # high AI score shouldn't save this
        moat_total=0.0, market_cap_yi=10.0, is_safe=False,
    )
    maotai = compute_investment_score(_MAOTAI)["score"]
    spec   = compute_investment_score(pure_speculation)["score"]
    assert maotai > spec, (
        f"Maotai ({maotai:.1f}) must outscore pure speculation ({spec:.1f})"
    )


# ═══════════════════════════════════════════════════════════════
# 4 · FIELD-CONTRACT SMOKE TESTS
# ═══════════════════════════════════════════════════════════════

def test_dim15_field_contract():
    """dim_15 must score higher when recent_news is populated vs empty (P0-B fix)."""
    raw_with_news = _make_raw({
        "15_events": {"data": {
            "recent_news": [{"title": f"正面新闻标题 {i}"} for i in range(30)],
            "recent_notices": [],
        }}
    })
    raw_empty = _make_raw({
        "15_events": {"data": {}}
    })

    result_with   = score_dimensions(raw_with_news)
    result_empty  = score_dimensions(raw_empty)

    score_with  = result_with["dimensions"]["15_events"]["score"]
    score_empty = result_empty["dimensions"]["15_events"]["score"]

    assert score_with > score_empty, (
        f"dim_15 should be higher with 30 news items ({score_with}) "
        f"than with empty events ({score_empty}) — P0-B field mismatch regression"
    )


def test_dim15_negative_news_not_rewarded():
    """Negative news should NOT increase dim_15 score above neutral baseline."""
    neg_kws = ["暴雷", "违规", "处罚", "退市"]
    raw_neg = _make_raw({
        "15_events": {"data": {
            "recent_news": [{"title": f"{kw} 公告"} for kw in neg_kws * 5],  # 20 negative items
            "recent_notices": [],
        }}
    })
    raw_empty = _make_raw({"15_events": {"data": {}}})

    score_neg   = score_dimensions(raw_neg)["dimensions"]["15_events"]["score"]
    score_empty = score_dimensions(raw_empty)["dimensions"]["15_events"]["score"]

    assert score_neg <= score_empty, (
        f"Negative news should not raise dim_15 above neutral {score_empty}; "
        f"got {score_neg} — sentiment filter regression"
    )


def test_moat_dim_reads_real_scores():
    """dim_14 must return a real score (not the stub 6) when moat.scores is populated."""
    raw_high_moat = _make_raw({
        "14_moat": {"data": {
            "scores": {"intangible": 9, "switching": 8, "network": 7, "scale": 8}  # total 32/40
        }}
    })
    raw_no_moat = _make_raw({
        "14_moat": {"data": {
            "scores": {"intangible": 1, "switching": 1, "network": 1, "scale": 1}  # total 4/40
        }}
    })

    score_high = score_dimensions(raw_high_moat)["dimensions"]["14_moat"]["score"]
    score_low  = score_dimensions(raw_no_moat)["dimensions"]["14_moat"]["score"]

    assert score_high > score_low, (
        f"dim_14 must differentiate moat scores: high={score_high} low={score_low}"
    )
    assert score_high >= 7, f"Moat 32/40 should map to ≥7, got {score_high}"
    assert score_low <= 2, f"Moat 4/40 should map to ≤2, got {score_low}"


def test_rev_growth_alias_bridge():
    """rev_growth_3y and rev_growth_yoy must NOT be zero when revenue_growth_3y_cagr is set.
    (P0-A regression guard: alias bridge in extract_features must populate old key names)
    """
    # Import the wrapped extract_features (which applies the alias bridge)
    from lib.stock_features import extract_features
    raw = {
        "ticker": "TEST",
        "dimensions": {
            "1_financials": {"data": {
                "roe": 15.0, "roe_history": [12, 14, 15],
                "net_margin": 15.0,
                "revenue_history": [800, 900, 1000, 1150],  # 3Y CAGR ≈ 13%
                "financial_health": {"debt_ratio": 30.0},
            }},
        },
        "market": "US",
    }
    f = extract_features(raw)
    cagr = f.get("revenue_growth_3y_cagr", 0)
    alias = f.get("rev_growth_3y", None)
    assert alias is not None, "rev_growth_3y alias must be present in features dict"
    assert alias == cagr, (
        f"rev_growth_3y ({alias}) must equal revenue_growth_3y_cagr ({cagr}) — alias bridge broken"
    )
    assert alias != 0 or cagr == 0, (
        f"rev_growth_3y is 0 but cagr is {cagr} — alias bridge not populating"
    )


def test_weights_sum_to_one():
    """Five-axis weights in compute_investment_score must sum to exactly 1.00."""
    f = _make_features()
    result = compute_investment_score(f)
    total = sum(result["weights"].values())
    assert abs(total - 1.0) < 1e-9, (
        f"Weights must sum to 1.00, got {total:.10f}: {result['weights']}"
    )


def test_score_drift_record_smoke():
    """score_drift.record() must not raise when given a valid synthesis-like dict."""
    from lib.pipeline.score_drift import record
    import tempfile, os

    synthetic_synthesis = {
        "ticker": "SMOKE_TEST",
        "market": "US",
        "overall_score": 65.0,
        "investment_score": 62.0,
        "fundamental_score": 68.0,
        "panel_consensus": 58.0,
        "investment_scorecard": {
            "score": 62.0,
            "axes": {"quality": 70.0, "growth": 60.0, "catalyst": 55.0,
                     "valuation": 50.0, "risk_control": 65.0},
        },
    }
    synthetic_panel = {
        "panel_consensus": 58.0,
        "vote_distribution": {"strongly_buy": 3, "buy": 10, "watch": 8,
                               "wait": 12, "avoid": 5, "skip": 10},
        "consensus_formula": {"polarize_k": 1.28},
    }

    # Temporarily redirect cache dir to a temp dir to avoid polluting real cache
    orig_env = os.environ.get("UZI_CACHE_DIR")
    with tempfile.TemporaryDirectory() as td:
        os.environ["UZI_CACHE_DIR"] = td
        try:
            record("SMOKE_TEST", synthetic_synthesis, synthetic_panel)
            # Verify the JSONL file was created and contains valid JSON
            import json
            from pathlib import Path
            hist = Path(td) / "_global" / "score_history.jsonl"
            assert hist.exists(), "score_history.jsonl not created"
            entries = [json.loads(line) for line in hist.read_text().splitlines() if line]
            assert len(entries) == 1
            e = entries[0]
            assert e["overall"] == 65.0
            assert e["buy_score"] == 62.0
            assert e["fundamental"] == 68.0
            assert e["panel_consensus"] == 58.0
            assert e["polarize_k"] == 1.28
        finally:
            if orig_env is None:
                os.environ.pop("UZI_CACHE_DIR", None)
            else:
                os.environ["UZI_CACHE_DIR"] = orig_env


def test_score_drift_record_missing_panel():
    """score_drift.record() must handle missing panel gracefully (active_count=None, polarize_k=None)."""
    from lib.pipeline.score_drift import record
    import tempfile, os, json
    from pathlib import Path

    synth = {"ticker": "T", "market": "US", "overall_score": 60.0,
             "investment_score": 55.0, "fundamental_score": 62.0,
             "panel_consensus": 52.0, "investment_scorecard": {}}
    with tempfile.TemporaryDirectory() as td:
        os.environ["UZI_CACHE_DIR"] = td
        try:
            record("T", synth, panel=None)  # no panel
            hist = Path(td) / "_global" / "score_history.jsonl"
            e = json.loads(hist.read_text().strip())
            assert e["overall"] == 60.0
            # active_count and polarize_k should be None/0 but not raise
            assert e.get("polarize_k") is None
        finally:
            os.environ.pop("UZI_CACHE_DIR", None)
