#!/usr/bin/env python3
"""Freeze and score a real Yahoo US issuer entity-matching shadow dataset.

The online step only fetches Yahoo Finance search results.  Labels are stored
separately and replayed offline so production and candidate matchers see the
same titles.  SEC is intentionally not contacted here: the caller must record
an access gap when no truthful SEC contact identity is configured.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fetch_events import _news_matches_entity  # noqa: E402
from lib.us_entity_matching import (  # noqa: E402
    US_ENTITY_PROFILES,
    matches_us_news_entity,
)


YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
ENTITY_STOPWORDS = {
    "company", "corporation", "corp", "group", "holding", "holdings",
    "inc", "incorporated", "limited", "ltd", "markets", "motor", "plc",
    "technology", "technologies",
}
COMMON_WORD_TICKERS = {"AI", "C", "F", "IT", "ON", "CAT", "GEN"}


PROFILES: dict[str, dict[str, Any]] = {
    "MU": {
        "legal_name": "Micron Technology, Inc.",
        "selection_reason": "短 ticker；验证 MU 不回退为 Musk substring 污染。",
        "aliases": [],
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
        "selection_reason": "NortonLifeLock 更名且多品牌；检验 Norton/Avast/LifeLock 召回。",
        "aliases": [
            {
                "value": "Gen",
                "kind": "issuer_short_brand",
                "source_url": "https://investor.gendigital.com/news/news-details/2022/Introducing-Gen-The-Company-to-Power-Digital-Freedom/default.aspx",
                "binding": "Gen IR introduces Gen as Nasdaq: GEN issuer short brand",
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
# The production registry is the single source of truth.  The literal above is
# retained only for backward readability of older frozen snapshots.
PROFILES = US_ENTITY_PROFILES


def _canonical_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return value.strip()
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def _row_id(ticker: str, url: str, title: str) -> str:
    material = f"{ticker}\n{_canonical_url(url)}\n{title.strip()}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:16]


def _bounded(text: str, value: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", text, re.I))


def _qualified_ticker(text: str, ticker: str) -> bool:
    escaped = re.escape(ticker)
    patterns = (
        rf"\${escaped}(?![A-Za-z0-9])",
        rf"\(\s*{escaped}\s*\)",
        rf"\b(?:NASDAQ|NYSE)\s*:\s*{escaped}\b",
        rf"\b{escaped}\s+(?:stock|shares|earnings|investors?)\b",
    )
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def candidate_matches(
    title: str,
    summary: str,
    ticker: str,
    profile: dict[str, Any],
    *,
    related_tickers: list[str] | None = None,
    publisher: str = "",
) -> bool:
    """Delegate to the exact production candidate matcher."""
    return matches_us_news_entity(
        title,
        summary,
        ticker,
        ticker,
        str(profile["legal_name"]),
    )


def _load_profiles(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return PROFILES
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", payload)
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("profiles file must contain a non-empty object")
    return {str(ticker).upper(): dict(profile) for ticker, profile in profiles.items()}


def fetch_snapshot(profiles: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    captured_at = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    latencies: dict[str, float] = {}
    profiles = profiles or PROFILES
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; UZI-Skill Yahoo shadow)"})
    for ticker, profile in profiles.items():
        queries = list(dict.fromkeys([ticker, *(profile.get("search_queries") or [])]))
        seen_ids: set[str] = set()
        query_latencies: list[float] = []
        for query in queries:
            started = time.perf_counter()
            response = session.get(
                YAHOO_SEARCH_URL,
                params={
                    "q": query,
                    "quotesCount": 1,
                    "newsCount": 10,
                    "enableFuzzyQuery": "false",
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            query_latencies.append(time.perf_counter() - started)
            for rank, item in enumerate(payload.get("news") or []):
                title = str(item.get("title") or "").strip()
                url = str(item.get("link") or "").strip()
                row_id = _row_id(ticker, url, title)
                if row_id in seen_ids:
                    continue
                seen_ids.add(row_id)
                published_epoch = item.get("providerPublishTime")
                published_utc = None
                if isinstance(published_epoch, (int, float)):
                    published_utc = datetime.fromtimestamp(published_epoch, timezone.utc).isoformat()
                summary = str(item.get("summary") or "").strip()
                rows.append(
                    {
                        "id": row_id,
                        "ticker": ticker,
                        "search_query": query,
                        "rank": rank,
                        "title": title,
                        "summary": summary,
                        "url": url,
                        "canonical_url": _canonical_url(url),
                        "publisher": item.get("publisher"),
                        "published_utc": published_utc,
                        "related_tickers": item.get("relatedTickers") or [],
                        "baseline_match": _news_matches_entity(
                            title, summary, ticker, ticker, profile["legal_name"]
                        ),
                        "candidate_match": candidate_matches(
                            title,
                            summary,
                            ticker,
                            profile,
                            related_tickers=item.get("relatedTickers") or [],
                            publisher=str(item.get("publisher") or ""),
                        ),
                    }
                )
        latencies[ticker] = round(sum(query_latencies), 6)
    return {
        "schema": "uzi.us_entity_recall_shadow.v1",
        "captured_at_utc": captured_at.isoformat(),
        "source": YAHOO_SEARCH_URL,
        "request": {
            "quotesCount": 1,
            "newsCount": 10,
            "enableFuzzyQuery": "false",
            "query_policy": "ticker plus optional source-bound profile search_queries; de-duplicate within ticker",
        },
        "profiles": profiles,
        "sec_access": {
            "attempted": False,
            "status": "gap",
            "reason": "No truthful SEC contact identity was configured; SEC network requests were not made.",
        },
        "latency_seconds": latencies,
        "rows": rows,
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def evaluate(snapshot: dict[str, Any], labels: dict[str, Any]) -> dict[str, Any]:
    label_rows = labels.get("labels") or {}
    default_truth = labels.get("default_truth")
    if default_truth not in {None, "relevant", "irrelevant", "ambiguous"}:
        raise ValueError(f"invalid default_truth: {default_truth}")
    allowed = {"true_positive", "false_positive", "false_negative", "ambiguous"}
    results: dict[str, Any] = {}
    now = datetime.fromisoformat(str(snapshot["captured_at_utc"]).replace("Z", "+00:00"))

    for matcher_key in ("baseline_match", "candidate_match"):
        counts = Counter()
        accepted = 0
        judged_relevant = 0
        ages: list[float] = []
        details: list[dict[str, Any]] = []
        for row in snapshot["rows"]:
            label_data = label_rows.get(row["id"])
            if not label_data and default_truth:
                label_data = {
                    "truth": default_truth,
                    "reason": labels.get("default_reason"),
                }
            if not label_data:
                counts["unlabeled"] += 1
                continue
            truth = str(label_data.get("truth"))
            if truth not in {"relevant", "irrelevant", "ambiguous"}:
                raise ValueError(f"invalid truth for {row['id']}: {truth}")
            if matcher_key == "candidate_match":
                profile = (snapshot.get("profiles") or PROFILES)[row["ticker"]]
                matched = candidate_matches(
                    row.get("title", ""),
                    row.get("summary", ""),
                    row["ticker"],
                    profile,
                    related_tickers=row.get("related_tickers", []),
                    publisher=row.get("publisher", ""),
                )
            else:
                matched = bool(row[matcher_key])
            if truth == "ambiguous":
                verdict = "ambiguous"
            elif matched and truth == "relevant":
                verdict = "true_positive"
            elif matched:
                verdict = "false_positive"
            elif truth == "relevant":
                verdict = "false_negative"
            else:
                verdict = "true_negative"
            if verdict not in allowed and verdict != "true_negative":
                raise AssertionError(verdict)
            counts[verdict] += 1
            accepted += int(matched)
            judged_relevant += int(truth == "relevant")
            if row.get("published_utc"):
                published = datetime.fromisoformat(str(row["published_utc"]).replace("Z", "+00:00"))
                ages.append(max(0.0, (now - published).total_seconds() / 86400))
            details.append(
                {
                    "id": row["id"],
                    "ticker": row["ticker"],
                    "title": row["title"],
                    "truth": truth,
                    "verdict": verdict,
                    "reason": label_data.get("reason"),
                }
            )
        tp, fp, fn = counts["true_positive"], counts["false_positive"], counts["false_negative"]
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        results[matcher_key] = {
            "counts": dict(counts),
            "accepted": accepted,
            "judged_relevant": judged_relevant,
            "precision": precision,
            "recall": recall,
            "cross_issuer_contamination_rate": fp / accepted if accepted else None,
            "details": details,
            "freshness_days": {
                "median": statistics.median(ages) if ages else None,
                "p95": _percentile(ages, 0.95),
                "within_7d_rate": sum(age <= 7 for age in ages) / len(ages) if ages else None,
                "within_30d_rate": sum(age <= 30 for age in ages) / len(ages) if ages else None,
                "within_90d_rate": sum(age <= 90 for age in ages) / len(ages) if ages else None,
            },
        }

    keys = [(row["ticker"], row["canonical_url"] or row["title"].lower()) for row in snapshot["rows"]]
    unique_keys = set(keys)
    latencies = [float(value) for value in snapshot.get("latency_seconds", {}).values()]
    return {
        "schema": "uzi.us_entity_recall_shadow_metrics.v1",
        "captured_at_utc": snapshot["captured_at_utc"],
        "rows": len(snapshot["rows"]),
        "labeled_rows": sum(
            1 for row in snapshot["rows"] if row["id"] in label_rows or default_truth
        ),
        "duplicate_rate": (len(keys) - len(unique_keys)) / len(keys) if keys else None,
        "latency_seconds": {
            "median": statistics.median(latencies) if latencies else None,
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
        },
        "matchers": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--metrics-out", type=Path)
    parser.add_argument(
        "--profiles",
        type=Path,
        help="Optional JSON profile set for an independent holdout capture.",
    )
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()

    if args.fetch:
        snapshot = fetch_snapshot(_load_profiles(args.profiles))
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))

    if args.labels:
        labels = json.loads(args.labels.read_text(encoding="utf-8"))
        metrics = evaluate(snapshot, labels)
        rendered = json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"
        if args.metrics_out:
            args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
            args.metrics_out.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
    else:
        print(f"snapshot rows: {len(snapshot['rows'])}")
        print(f"snapshot: {args.snapshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
