"""Dimension 3 · 宏观环境 — 真实 web search 拉取利率/汇率/地缘/大宗."""
from __future__ import annotations

import json
import sys
from datetime import datetime

from lib.fred_source import fetch_fred_macro_snapshot
from lib.web_search import search, search_trusted


def main(industry: str = "综合", market: str = "A") -> dict:
    year = datetime.now().year
    market = (market or "A").upper()
    is_global = market in {"U", "G"}
    # v2.7.3 · 利率/政策/汇率用 3_macro 权威域（stats.gov.cn / pbc / safe / 中证网...）
    # 行业宏观 + 大宗商品用普通 search（覆盖面更广）
    trusted_queries = {
        "rate_cycle": f"{year} 中国 利率 货币政策 降息 最新",
        "us_rate": f"{year} 美联储 利率周期 最新",
        "fx_trend": (
            f"{year} 美元指数 DXY 汇率走势"
            if is_global
            else f"{year} 人民币 汇率 走势"
        ),
    }
    generic_queries = {
        "geo_risk": f"{year} 中美关系 贸易 制裁 {industry}",
        "commodity": f"{year} 大宗商品 周期 CRB指数",
        "industry_macro": f"{year} {industry} 宏观 政策 利好 利空",
    }

    snippets: dict[str, list] = {}
    for key, q in trusted_queries.items():
        res = search_trusted(q, dim_key="3_macro", max_results=4)
        valid = [r for r in res if "error" not in r]
        snippets[key] = [
            {"title": r.get("title", "")[:80], "body": r.get("body", "")[:200], "url": r.get("url", "")}
            for r in valid[:3]
        ]
    for key, q in generic_queries.items():
        res = search(q, max_results=4)
        valid = [r for r in res if "error" not in r]
        snippets[key] = [
            {"title": r.get("title", "")[:80], "body": r.get("body", "")[:200], "url": r.get("url", "")}
            for r in valid[:3]
        ]

    # Quick sentiment extraction from snippets (heuristic)
    def _sentiment(bodies: list[str]) -> str | None:
        text = " ".join(body.strip() for body in bodies if body and body.strip()).lower()
        if not text:
            return None
        pos = sum(1 for kw in ["降息", "宽松", "利好", "稳定", "回暖"] if kw.lower() in text)
        neg = sum(1 for kw in ["加息", "紧缩", "利空", "下行", "衰退"] if kw.lower() in text)
        if pos > neg + 1:
            return "利好"
        if neg > pos + 1:
            return "利空"
        return "中性"

    def _bodies(key: str) -> list[str]:
        return [s.get("body", "") for s in snippets.get(key, [])]

    rate_key = "us_rate" if is_global else "rate_cycle"
    rate_cycle = _sentiment(_bodies(rate_key))
    fx_trend = _sentiment(_bodies("fx_trend"))
    geo_risk = _sentiment(_bodies("geo_risk"))
    commodity = _sentiment(_bodies("commodity"))
    industry_macro = _sentiment(_bodies("industry_macro"))
    has_evidence = any(snippets.values())
    official_macro = None
    if is_global:
        try:
            official_macro = fetch_fred_macro_snapshot()
        except Exception as exc:
            official_macro = {
                "status": "gap",
                "reason": type(exc).__name__,
                "observations": {},
            }

    return {
        "data": {
            "rate_cycle": (
                f"{rate_cycle}（{year} {'美联储利率' if is_global else '中国货币政策'}）"
                if rate_cycle else None
            ),
            "fx_trend": (
                f"{fx_trend}（{'美元指数' if is_global else '人民币走势'}）"
                if fx_trend else None
            ),
            "geo_risk": f"{geo_risk}（地缘风险）" if geo_risk else None,
            "commodity": f"{commodity}（大宗周期）" if commodity else None,
            "industry_macro_impact": industry_macro,
            "web_search_snippets": snippets,
            "year": year,
            "industry": industry,
            "market": market,
            "rate_market": "US" if is_global else "CN",
            "official_macro_observations": official_macro,
        },
        "source": (
            "web_search:ddgs + heuristic sentiment + FRED official observations (shadow)"
            if is_global else "web_search:ddgs + heuristic sentiment"
        ),
        "fallback": not has_evidence,
    }


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "光学光电子"
    print(json.dumps(main(arg), ensure_ascii=False, indent=2, default=str))
