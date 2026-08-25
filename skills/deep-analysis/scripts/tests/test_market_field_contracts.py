"""Market/depth contract regressions for report data-quality presentation."""
from __future__ import annotations


CORE = [
    "0_basic", "1_financials", "2_kline", "10_valuation",
    "11_governance", "15_events", "16_lhb",
]


def _raw(market: str, ticker: str, depth: str = "lite") -> dict:
    dims = {
        "0_basic": {"data": {"name": "Test", "price": 10, "industry": "Semiconductors",
                               "market_cap": 100, "pe_ttm": 20, "pb": 2}},
        "1_financials": {"data": {"roe_history": [10, 11], "revenue_history": [1, 2],
                                    "net_profit_history": [1, 2], "financial_health": {"ok": True}}},
        "2_kline": {"data": {"stage": "Stage 2", "ma_align": "bull", "macd": "up"}},
        "10_valuation": {"data": {"pe": 20, "pe_quantile": 30, "pb_quantile": 40}},
        "11_governance": {"data": {"evidence": "available"}},
        "15_events": {"data": {"evidence": "available"}},
        "16_lhb": {"data": {"_note": "lhb only A-share"}, "source": "skip"},
    }
    return {
        "ticker": ticker,
        "market": market,
        "analysis_profile": {"depth": depth},
        "fetchers_enabled": list(CORE),
        "dimensions": dims,
    }


def test_us_lite_does_not_call_a_share_fields_missing():
    from lib.data_integrity import validate

    report = validate(_raw("U", "NVDA"))
    missing = {x["dim"] for x in report["missing_enrichment"]}
    assert "12_capital_flow" not in missing
    assert "16_lhb" not in missing
    na = {x["dim"] for x in report["not_applicable"]}
    assert {"12_capital_flow", "16_lhb"}.issubset(na)
    assert report["coverage_pct"] == 100


def test_us_recovery_uses_sec_yahoo_not_a_share_routes():
    from lib.data_integrity import generate_recovery_tasks, validate

    raw = _raw("U", "NVDA")
    raw["dimensions"]["1_financials"]["data"]["roe_history"] = None
    integrity = validate(raw)
    tasks = generate_recovery_tasks(raw, integrity)
    roe = next(x for x in tasks if x["field"] == "roe_history")
    actions = " ".join(roe["suggested_actions"]).lower()
    assert "sec:" in actions and "yahoo:" in actions
    assert "xueqiu" not in actions and "北向" not in actions


def test_hk_capital_flow_uses_southbound_label():
    from lib.data_integrity import validate

    raw = _raw("H", "00700.HK", depth="medium")
    raw["fetchers_enabled"] = list(CORE) + ["12_capital_flow"]
    report = validate(raw)
    item = next(x for x in report["missing_enrichment"] if x["dim"] == "12_capital_flow")
    assert "港股通" in item["label"] or "南向" in item["label"]


def test_a_share_capital_flow_keeps_a_share_semantics():
    from lib.market_field_contracts import presentation_for

    label = presentation_for("12_capital_flow", "A")["label"]
    assert "融资融券" in label
    assert "南向" not in label


def test_us_lite_renderer_hides_disabled_and_not_applicable_cards():
    from assemble_report import render_dim_category

    raw = _raw("U", "NVDA")
    dimensions = {"dimensions": {key: {"score": 5, "label": "neutral"} for key in CORE}}
    html = render_dim_category("mkt", dimensions, raw)
    assert 'data-dim="02"' in html
    assert 'data-dim="12"' not in html
    assert 'data-dim="16"' not in html
    assert "北向" not in html and "龙虎榜" not in html


def test_banner_does_not_claim_unrun_recovery_methods():
    from lib.report.institutional import _render_data_gap_banner

    gaps = {
        "analysis_depth": "lite", "coverage_pct": 90, "unresolved": 1,
        "tasks": [{"label": "ROE 历史", "dim": "1_financials",
                   "severity": "critical", "status": "pending"}],
    }
    html = _render_data_gap_banner(gaps, raw=_raw("U", "NVDA"))
    assert "不作“已尝试”声明" in html
    assert "Agent 已尝试浏览器抓取" not in html


def test_stage2_review_uses_persisted_lite_profile(monkeypatch):
    from lib.self_review import check_agent_analysis_exists, check_all_dims_exist

    monkeypatch.setenv("UZI_DEPTH", "medium")
    raw = _raw("U", "NVDA")
    ctx = {"raw": raw, "dims": raw["dimensions"], "ag": None}
    assert check_all_dims_exist(ctx) == []
    issues = check_agent_analysis_exists(ctx)
    assert len(issues) == 1
    assert issues[0].severity == "warning"
