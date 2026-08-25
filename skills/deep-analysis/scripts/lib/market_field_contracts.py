"""Market applicability contract for report dimensions and integrity checks.

Keep three states distinct: applicable and enabled; applicable but intentionally
disabled by the selected depth; and not applicable to the current market.
This module changes presentation/integrity only, never scores or thresholds.
"""
from __future__ import annotations

from typing import Any


MARKET_LABELS = {"A": "A 股", "H": "港股", "U": "美股", "G": "全球其他市场"}

# Current collector support. Similar concepts elsewhere must not be presented
# under an A-share label until a validated adapter is wired into UZI.
DIM_MARKETS: dict[str, frozenset[str]] = {
    "6_research": frozenset({"A"}),
    "12_capital_flow": frozenset({"A", "H"}),
    "16_lhb": frozenset({"A"}),
}

DIM_PRESENTATION: dict[str, dict[str, dict[str, Any]]] = {
    "12_capital_flow": {
        "A": {"title": "A 股资金面", "en": "A-share Flows", "label": "北向/融资融券/股东户数"},
        "H": {"title": "港股通与资金面", "en": "Southbound & Flows", "label": "港股通资格/南向观察"},
    },
    "16_lhb": {"A": {"title": "龙虎榜", "en": "Dragon-Tiger", "label": "龙虎榜/游资"}},
    "17_sentiment": {
        "A": {"title": "舆情与大V", "en": "Sentiment", "label": "市场舆情"},
        "H": {"title": "市场舆情", "en": "Market Sentiment", "label": "市场舆情"},
        "U": {"title": "市场舆情", "en": "Market Sentiment", "label": "市场舆情"},
        "G": {"title": "市场舆情", "en": "Market Sentiment", "label": "市场舆情"},
    },
    "18_trap": {
        "A": {"title": "杀猪盘检测", "en": "Trap Scan", "label": "推广操纵风险"},
        "H": {"title": "推广操纵风险", "en": "Promotion Risk", "label": "推广操纵风险"},
        "U": {"title": "推广操纵风险", "en": "Promotion Risk", "label": "推广操纵风险"},
        "G": {"title": "推广操纵风险", "en": "Promotion Risk", "label": "推广操纵风险"},
    },
    "19_contests": {
        "A": {"title": "实盘比赛持仓", "en": "Live Contests", "label": "公开组合/实盘比赛"},
        "H": {"title": "公开组合持仓", "en": "Public Portfolios", "label": "公开组合持仓"},
        "U": {"title": "公开组合持仓", "en": "Public Portfolios", "label": "公开组合持仓"},
        "G": {"title": "公开组合持仓", "en": "Public Portfolios", "label": "公开组合持仓"},
    },
    "6_research": {
        "A": {"title": "券商研报", "en": "Sell-side", "label": "券商研报"},
        "H": {"title": "分析师预期", "en": "Analyst Estimates", "label": "分析师预期"},
        "U": {"title": "分析师预期", "en": "Analyst Estimates", "label": "分析师预期"},
        "G": {"title": "分析师预期", "en": "Analyst Estimates", "label": "分析师预期"},
    },
}


def market_of(raw: dict | None) -> str:
    market = str((raw or {}).get("market") or "").upper()
    if market in MARKET_LABELS:
        return market
    ticker = str((raw or {}).get("ticker") or "")
    try:
        from lib.market_router import parse_ticker
        parsed = parse_ticker(ticker).market
        return parsed if parsed in MARKET_LABELS else "G"
    except Exception:
        return "A"


def is_dim_applicable(dim_key: str, market: str) -> bool:
    allowed = DIM_MARKETS.get(dim_key)
    return allowed is None or market in allowed


def presentation_for(dim_key: str, market: str) -> dict[str, Any]:
    variants = DIM_PRESENTATION.get(dim_key) or {}
    return dict(variants.get(market) or variants.get("A") or {})


def enabled_dims_for_raw(raw: dict | None) -> set[str] | None:
    """Return persisted enabled dims; do not guess for old cache snapshots."""
    if not isinstance(raw, dict):
        return None
    explicit = raw.get("fetchers_enabled")
    if isinstance(explicit, (list, tuple, set)):
        return {str(x) for x in explicit}
    profile = raw.get("analysis_profile")
    depth = profile.get("depth") if isinstance(profile, dict) else raw.get("analysis_depth")
    if depth in ("lite", "medium", "deep"):
        from lib.analysis_profile import get_profile
        return set(get_profile(str(depth)).fetchers_enabled)
    return None


def market_recovery_hints(market: str, dim_key: str, field: str) -> list[str] | None:
    """Market-correct recovery routes; placeholders are rendered by caller."""
    if market == "U":
        return {
            ("1_financials", "roe_history"): ["sec: '{code} companyfacts ROE inputs'", "yahoo: '{code} historical financials'"],
            ("10_valuation", "pe_quantile"): ["derive: Yahoo historical price + SEC/Yahoo earnings"],
            ("10_valuation", "pb_quantile"): ["derive: Yahoo historical price + SEC/Yahoo book value"],
            ("6_research", "_entire_dim"): ["yahoo: '{code} analyst estimates and target prices'"],
            ("7_industry", "growth"): ["ws: '{industry} US industry growth 2026'"],
            ("14_moat", "scores"): ["agent: SEC filings + official IR competitive evidence"],
        }.get((dim_key, field))
    if market == "H":
        return {
            ("6_research", "_entire_dim"): ["yahoo: '{code} analyst estimates and target prices'"],
            ("12_capital_flow", "_entire_dim"): ["source: 港股通资格与授权渠道的南向数据"],
        }.get((dim_key, field))
    return None

