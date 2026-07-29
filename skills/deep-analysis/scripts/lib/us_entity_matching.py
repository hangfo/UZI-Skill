"""Precision-first US news issuer matching with source-bound aliases.

Aliases in this registry are admitted only when an issuer-controlled investor
relations page proves the relationship.  Common-word tickers never match as
plain English words.
"""
from __future__ import annotations

import re
from typing import Any


ENTITY_STOPWORDS = {
    "company", "corporation", "corp", "digital", "group", "holding",
    "holdings", "inc", "incorporated", "limited", "ltd", "markets", "motor",
    "plc", "semiconductor", "strategy", "technology", "technologies",
}
COMMON_WORD_TICKERS = {"AI", "C", "F", "IT", "ON", "CAT", "GEN"}


US_ENTITY_PROFILES: dict[str, dict[str, Any]] = {
    "MU": {
        "legal_name": "Micron Technology, Inc.",
        "selection_reason": "短 ticker；验证 MU 不回退为 Musk substring 污染。",
        "aliases": [],
    },
    "MSTR": {
        "legal_name": "Strategy Inc.",
        "selection_reason": "公司由 MicroStrategy 更名为普通词 Strategy；旧名召回与新名精度必须同时受控。",
        "aliases": [
            {
                "value": "MicroStrategy",
                "kind": "former_legal_name",
                "source_url": "https://www.strategy.com/company",
                "binding": "Strategy official company page states that it rebranded from MicroStrategy in February 2025",
            },
            {
                "value": "Strategy",
                "kind": "issuer_short_brand",
                "source_url": "https://www.strategy.com/investor-relations",
                "binding": "Strategy investor relations binds Strategy to Nasdaq: MSTR",
                "patterns": [
                    r"^Strategy\s+(?:to|Reports?|Announces?|Launches?|Completes?|Acquires?|Buys?|Purchases?|Adds?|Holds?|Raises?|Offers?|Prices?)\b",
                    r"^Strategy\s+\((?:NASDAQ\s*:\s*)?MSTR\)\b",
                ],
            },
        ],
    },
    "AI": {
        "legal_name": "C3.ai, Inc.",
        "selection_reason": "短 ticker 且 AI 是普通词；验证跨发行人污染。",
        "aliases": [
            {
                "value": "C3.ai",
                "kind": "issuer_brand",
                "source_url": "https://ir.c3.ai/",
                "binding": "C3.ai issuer investor-relations site",
            },
        ],
    },
    "C": {
        "legal_name": "Citigroup Inc.",
        "selection_reason": "单字符 ticker；验证普通字母不能独立作为实体证据。",
        "aliases": [
            {
                "value": "Citi",
                "kind": "issuer_brand",
                "source_url": "https://www.citigroup.com/global/news/press-release/2026/citi-2026-investor-day",
                "binding": "Citigroup official release binds Citigroup Inc. (NYSE: C) to Citi",
            },
        ],
    },
    "F": {
        "legal_name": "Ford Motor Company",
        "selection_reason": "单字符 ticker；以强法人品牌作为控制。",
        "aliases": [],
    },
    "GOOGL": {
        "legal_name": "Alphabet Inc.",
        "provider_symbols": ["GOOGL", "GOOG"],
        "selection_reason": "品牌名与法人名不同；检验 Google 召回。",
        "aliases": [
            {
                "value": "Google",
                "kind": "controlled_subsidiary",
                "source_url": "https://abc.xyz/investor/news/news-details/2026/Google-Completes-Acquisition-of-Wiz-2026-ta7OaU2uA0/default.aspx",
                "binding": "Alphabet IR states Google is a subsidiary of Alphabet Inc.",
            },
        ],
    },
    "META": {
        "legal_name": "Meta Platforms, Inc.",
        "selection_reason": "法人名与多品牌组合；检验品牌边界。",
        "aliases": [
            {
                "value": "Facebook",
                "kind": "reportable_segment_brand",
                "source_url": "https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Fourth-Quarter-and-Full-Year-2025-Results/",
                "binding": "Meta IR Family of Apps includes Facebook",
            },
            {
                "value": "Instagram",
                "kind": "reportable_segment_brand",
                "source_url": "https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Fourth-Quarter-and-Full-Year-2025-Results/",
                "binding": "Meta IR Family of Apps includes Instagram",
            },
            {
                "value": "WhatsApp",
                "kind": "reportable_segment_brand",
                "source_url": "https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Fourth-Quarter-and-Full-Year-2025-Results/",
                "binding": "Meta IR Family of Apps includes WhatsApp",
            },
        ],
    },
    "HOOD": {
        "legal_name": "Robinhood Markets, Inc.",
        "selection_reason": "消费者品牌与法人后缀不同；验证 Robinhood token。",
        "aliases": [],
    },
    "ON": {
        "legal_name": "ON Semiconductor Corporation",
        "selection_reason": "普通词 ticker；同时覆盖官方 onsemi 品牌。",
        "aliases": [
            {
                "value": "onsemi",
                "kind": "issuer_brand",
                "source_url": "https://investor.onsemi.com/news-releases/news-release-details/onsemi-reports-fourth-quarter-and-full-year-2025-results-0",
                "binding": "onsemi IR binds Nasdaq: ON to the onsemi brand",
            },
        ],
    },
    "IT": {
        "legal_name": "Gartner, Inc.",
        "selection_reason": "普通词 ticker；验证 IT 不应匹配普通代词。",
        "aliases": [],
    },
    "CAT": {
        "legal_name": "Caterpillar Inc.",
        "selection_reason": "常见词 ticker；以强法人品牌作为控制。",
        "aliases": [],
    },
    "XYZ": {
        "legal_name": "Block, Inc.",
        "selection_reason": "公司更名且多品牌；检验 Square/Cash App 召回。",
        "aliases": [
            {
                "value": "Square",
                "kind": "issuer_business_brand",
                "source_url": "https://investors.block.xyz/investor-news/news-details/2021/Square-Inc.-Changes-Name-to-Block/default.aspx",
                "binding": "Block IR states Square remains its Seller business brand",
            },
            {
                "value": "Cash App",
                "kind": "issuer_business_brand",
                "source_url": "https://investors.block.xyz/overview/default.aspx",
                "binding": "Block IR lists Cash App as a Block brand",
            },
        ],
    },
    "GEN": {
        "legal_name": "Gen Digital Inc.",
        "selection_reason": "NortonLifeLock 更名且多品牌；检验品牌与受控业务召回。",
        "aliases": [
            {
                "value": "Gen",
                "kind": "issuer_short_brand",
                "source_url": "https://investor.gendigital.com/news/news-details/2022/Introducing-Gen-The-Company-to-Power-Digital-Freedom/default.aspx",
                "binding": "Gen IR introduces Gen as Nasdaq: GEN issuer short brand",
                "patterns": [
                    r"^Gen\s+(?:to|Reports?|Announces?|Launches?|Completes?|Acquires?|Half-Year|Q[1-4]|Fiscal)\b",
                    r"^GEN\s+(?:Stock|Shares|Earnings|Grew)\b",
                ],
            },
            {
                "value": "Norton",
                "kind": "issuer_brand",
                "source_url": "https://investor.gendigital.com/news/news-details/2022/Introducing-Gen-The-Company-to-Power-Digital-Freedom/default.aspx",
                "binding": "Gen IR states Norton is a trusted Gen brand",
            },
            {
                "value": "Avast",
                "kind": "issuer_brand",
                "source_url": "https://investor.gendigital.com/news/news-details/2022/Introducing-Gen-The-Company-to-Power-Digital-Freedom/default.aspx",
                "binding": "Gen IR states Avast is a trusted Gen brand",
            },
            {
                "value": "LifeLock",
                "kind": "issuer_brand",
                "source_url": "https://investor.gendigital.com/news/news-details/2022/Introducing-Gen-The-Company-to-Power-Digital-Freedom/default.aspx",
                "binding": "Gen IR states LifeLock is a trusted Gen brand",
            },
            {
                "value": "NortonLifeLock",
                "kind": "former_legal_name",
                "source_url": "https://investor.gendigital.com/news/news-details/2022/Introducing-Gen-The-Company-to-Power-Digital-Freedom/default.aspx",
                "binding": "Gen IR documents NortonLifeLock Inc. changing its name to Gen Digital Inc.",
            },
            {
                "value": "MoneyLion",
                "kind": "controlled_business",
                "source_url": "https://investor.gendigital.com/news/news-details/2025/Gen-Completes-Acquisition-of-MoneyLion-Accelerating-the-Companys-Leadership-in-Financial-Wellness/default.aspx",
                "binding": "Gen IR states Gen completed its acquisition of MoneyLion",
            },
        ],
    },
}


def _bounded(text: str, value: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", text, re.I))


def _qualified_common_ticker(text: str, ticker: str) -> bool:
    escaped = re.escape(ticker)
    patterns = (
        rf"\${escaped}(?![A-Za-z0-9])",
        rf"\(\s*{escaped}\s*\)",
        rf"\b(?:NASDAQ|NYSE)\s*:\s*{escaped}\b",
        rf"\b{escaped}\s+(?:stock|shares|earnings|investors?)\b",
        rf"\b(?:vs\.?|versus)\s+{escaped}\b",
        rf"\b{escaped}\s+(?:vs\.?|versus)\b",
    )
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _legal_entity_values(company_name: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9]+", str(company_name or ""))
    distinctive = [
        token for token in tokens
        if len(token) >= 4 and token.lower() not in ENTITY_STOPWORDS
    ]
    base_tokens = [
        token for token in tokens
        if token.lower() not in {
            "company", "corporation", "corp", "inc", "incorporated", "limited", "ltd", "plc",
        }
    ]
    base_phrase = " ".join(base_tokens)
    has_non_stopword = any(token.lower() not in ENTITY_STOPWORDS for token in base_tokens)
    values = ([base_phrase] if len(base_phrase) >= 4 and has_non_stopword else []) + distinctive
    return list(dict.fromkeys(values))


def _secondary_only(text: str, value: str) -> bool:
    escaped = re.escape(value)
    issuer_qualifier = (
        rf"(?<![A-Za-z0-9])(?i:{escaped})\s+"
        rf"(?:Partner|Supplier|Customer)\s+[A-Z][A-Za-z0-9&.-]+"
    )
    if re.search(issuer_qualifier, text):
        return True
    patterns = (
        rf"\bformer\s+{escaped}\b",
        rf"\b(?:recognized|named)\b.{{0,100}}\b{escaped}\b",
        rf"\bdespite\s+{escaped}\s+(?:recognition|mention)\b",
        rf"\baccording\s+to\s+{escaped}\b",
        rf"\b(?:supplier|partner|customer)\b.{{0,80}}\b(?:to|of|for)\b.{{0,50}}\b{escaped}\b",
    )
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _alias_matches(text: str, alias: dict[str, Any]) -> bool:
    patterns = alias.get("patterns") or []
    if patterns:
        return any(re.search(pattern, text) for pattern in patterns)
    return _bounded(text, str(alias["value"]))


def profile_for_ticker(ticker: str) -> dict[str, Any] | None:
    symbol = str(ticker or "").upper()
    direct = US_ENTITY_PROFILES.get(symbol)
    if direct:
        return direct
    return next(
        (
            profile
            for profile in US_ENTITY_PROFILES.values()
            if symbol in profile.get("provider_symbols", [])
        ),
        None,
    )


def aliases_for_ticker(ticker: str) -> list[dict[str, Any]]:
    profile = profile_for_ticker(ticker)
    return list(profile.get("aliases") or []) if profile else []


def matches_us_news_entity(
    title: str,
    summary: str,
    ticker_code: str,
    ticker_full: str,
    company_name: str,
) -> bool:
    """Return True only for bounded issuer evidence or a sourced issuer alias."""
    text = f"{title} {summary}".strip()
    ticker = str(ticker_code or ticker_full or "").upper()
    if ticker in COMMON_WORD_TICKERS:
        if _qualified_common_ticker(text, ticker):
            return True
    else:
        for symbol in {ticker_code, ticker_full}:
            if symbol and _bounded(text, str(symbol).strip()):
                return True

    profile = profile_for_ticker(ticker)
    legal_name = str((profile or {}).get("legal_name") or company_name or "")
    entity_values = _legal_entity_values(legal_name)
    matched_values = [value for value in entity_values if _bounded(text, value)]
    if any(not _secondary_only(text, value) for value in matched_values):
        return True

    for alias in (profile or {}).get("aliases") or []:
        if _alias_matches(text, alias) and not _secondary_only(text, str(alias["value"])):
            return True
    return False
