from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "uzi.evidence_overlay.v1"
DEFAULT_TIMEOUT_SEC = 12
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

SUPPORTED_TARGETS = ("missing_financials", "negative_event")
SEC_FINANCIAL_CONCEPTS = {
    "revenue": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "assets": ("Assets",),
    "liabilities": ("Liabilities",),
    "equity": ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
}

NEGATIVE_EVENT_TAXONOMY = {
    "P0": {
        "label": "hard stop / financial statement trust risk",
        "decision_use": "must cap or downgrade until resolved",
        "sec_8k_items": {
            "1.03": "Bankruptcy or Receivership",
            "4.02": "Non-Reliance on Previously Issued Financial Statements or Audit Report",
        },
        "keywords": ("sec charges", "accounting fraud", "fraud", "bankruptcy", "receivership", "立案", "欺诈"),
    },
    "P1": {
        "label": "material risk escalation",
        "decision_use": "requires risk review and usually prevents high-confidence buy",
        "sec_8k_items": {
            "1.05": "Material Cybersecurity Incidents",
            "2.04": "Triggering Events That Accelerate or Increase a Direct Financial Obligation",
            "2.05": "Costs Associated with Exit or Disposal Activities",
            "2.06": "Material Impairments",
            "3.01": "Notice of Delisting or Failure to Satisfy a Continued Listing Rule",
            "4.01": "Changes in Registrant's Certifying Accountant",
        },
        "keywords": ("default", "delisting", "material impairment", "auditor resignation", "重大减值", "退市", "处罚"),
    },
    "P2": {
        "label": "context-dependent operating or legal risk",
        "decision_use": "evidence for review only; not enough for automatic hard downgrade",
        "sec_8k_items": {},
        "keywords": ("lawsuit", "recall", "investigation", "诉讼", "调查", "召回"),
    },
}

NEGATED_NEGATIVE_TERMS = ("no fraud", "no violation", "未发现", "无违规", "settled", "和解")


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "run.py").exists() and (parent / "skills").exists():
            return parent
    raise RuntimeError("could not locate UZI-Skill repo root")


ROOT = _find_repo_root()
CACHE = ROOT / "skills" / "deep-analysis" / "scripts" / ".cache"
DEFAULT_OUT_DIR = ROOT / "local-ops" / "state" / "evidence-overlays"


def build_overlay(
    ticker: str,
    target: str,
    *,
    network: bool = True,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
) -> dict[str, Any]:
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported target: {target}")
    started = time.perf_counter()
    market = market_for_ticker(ticker)
    overlay: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker,
        "market": market,
        "target": target,
        "status": "gap",
        "confidence": {"level": "low", "score": 0, "factors": []},
        "evidence": [],
        "field_mapping": {},
        "source_plan": source_plan_for(market, target),
        "errors": [],
        "fetched_at": _now_utc(),
        "performance": {},
        "guardrails": [
            "online evidence is frozen before branch comparison",
            "missing evidence stays a gap; do not infer facts",
            "same overlay must be reused for baseline and candidate refs",
        ],
    }

    if target == "missing_financials":
        _fill_missing_financials_overlay(overlay, network=network, timeout_sec=timeout_sec, max_items=max_items)
    elif target == "negative_event":
        _fill_negative_event_overlay(overlay, network=network, timeout_sec=timeout_sec, max_items=max_items)

    overlay["performance"]["elapsed_sec"] = round(time.perf_counter() - started, 3)
    _finalize_confidence(overlay)
    return overlay


def _fill_missing_financials_overlay(
    overlay: dict[str, Any],
    *,
    network: bool,
    timeout_sec: int,
    max_items: int,
) -> None:
    ticker = overlay["ticker"]
    market = overlay["market"]
    cache_fields = _financial_fields_from_cache(ticker)
    if cache_fields:
        overlay["field_mapping"]["cache_raw_data"] = cache_fields
        overlay["evidence"].append(
            _evidence_item(
                source="local_raw_data",
                url=str(CACHE / ticker / "raw_data.json"),
                title=f"Cached raw_data financial fields for {ticker}",
                published_at=None,
                fields=sorted(cache_fields),
            )
        )

    if market == "US" and network:
        try:
            cik, company_name = sec_cik_for_ticker(ticker, timeout_sec=timeout_sec)
            facts = fetch_sec_companyfacts(cik, timeout_sec=timeout_sec)
            sec_fields = extract_sec_financial_fields(facts, max_items=max_items)
            if sec_fields:
                overlay["field_mapping"]["sec_companyfacts"] = sec_fields
                overlay["evidence"].append(
                    _evidence_item(
                        source="sec_companyfacts",
                        url=SEC_COMPANYFACTS_URL.format(cik=f"{cik:010d}"),
                        title=f"SEC companyfacts for {company_name} ({ticker})",
                        published_at=_latest_filed_date(sec_fields),
                        fields=sorted(sec_fields),
                    )
                )
        except Exception as exc:  # noqa: BLE001 - evidence builder records errors instead of failing the run
            overlay["errors"].append({"source": "sec_companyfacts", "error": str(exc)[:300]})
    elif market == "US" and not network:
        overlay["errors"].append({"source": "sec_companyfacts", "error": "network disabled"})
    elif network:
        overlay["errors"].append(
            {
                "source": "online_financials",
                "error": f"no implemented official online adapter for market {market}",
            }
        )

    if _has_required_financial_fields(overlay["field_mapping"]):
        overlay["status"] = "ready"
    elif overlay["field_mapping"]:
        overlay["status"] = "partial"
    else:
        overlay["status"] = "gap"


def _fill_negative_event_overlay(
    overlay: dict[str, Any],
    *,
    network: bool,
    timeout_sec: int,
    max_items: int,
) -> None:
    ticker = overlay["ticker"]
    market = overlay["market"]
    cache_events = _negative_events_from_cache(ticker)
    if cache_events:
        overlay["field_mapping"]["cache_events"] = {"events": cache_events}
        overlay["evidence"].extend(cache_events)

    if market == "US" and network:
        try:
            cik, company_name = sec_cik_for_ticker(ticker, timeout_sec=timeout_sec)
            submissions = fetch_sec_submissions(cik, timeout_sec=timeout_sec)
            sec_events = extract_sec_negative_events(
                submissions,
                cik=cik,
                ticker=ticker,
                company_name=company_name,
                max_items=max_items,
            )
            if sec_events:
                overlay["field_mapping"]["sec_submissions"] = {
                    "events": [
                        {
                            "severity": item.get("severity"),
                            "event_type": item.get("event_type"),
                            "filing_date": item.get("published_at"),
                            "form": item.get("form"),
                            "accession": item.get("accession"),
                        }
                        for item in sec_events
                    ]
                }
                overlay["evidence"].extend(sec_events)
        except Exception as exc:  # noqa: BLE001 - evidence builder records errors instead of failing the run
            overlay["errors"].append({"source": "sec_submissions", "error": str(exc)[:300]})
    elif market == "US" and not network:
        overlay["errors"].append({"source": "sec_submissions", "error": "network disabled"})
    elif network:
        overlay["errors"].append(
            {
                "source": "negative_event_online",
                "error": f"no implemented official negative-event adapter for market {market}",
            }
        )
    else:
        overlay["errors"].append({"source": "negative_event_online", "error": "network disabled"})

    traceable_events = [
        item
        for item in overlay["evidence"]
        if item.get("url") and item.get("title") and item.get("severity") in {"P0", "P1", "P2", None}
    ]
    if any(item.get("severity") in {"P0", "P1"} for item in traceable_events):
        overlay["status"] = "ready"
    elif traceable_events:
        overlay["status"] = "partial"
    else:
        overlay["status"] = "gap"


def sec_cik_for_ticker(ticker: str, *, timeout_sec: int = DEFAULT_TIMEOUT_SEC) -> tuple[int, str]:
    data = _fetch_json(SEC_TICKERS_URL, timeout_sec=timeout_sec)
    target = ticker.upper()
    for row in data.values():
        if str(row.get("ticker", "")).upper() == target:
            return int(row["cik_str"]), str(row.get("title") or target)
    raise ValueError(f"SEC ticker mapping not found for {ticker}")


def fetch_sec_companyfacts(cik: int, *, timeout_sec: int = DEFAULT_TIMEOUT_SEC) -> dict[str, Any]:
    return _fetch_json(SEC_COMPANYFACTS_URL.format(cik=f"{cik:010d}"), timeout_sec=timeout_sec)


def fetch_sec_submissions(cik: int, *, timeout_sec: int = DEFAULT_TIMEOUT_SEC) -> dict[str, Any]:
    return _fetch_json(SEC_SUBMISSIONS_URL.format(cik=f"{cik:010d}"), timeout_sec=timeout_sec)


def extract_sec_financial_fields(companyfacts: dict[str, Any], *, max_items: int = 5) -> dict[str, Any]:
    facts = ((companyfacts.get("facts") or {}).get("us-gaap") or {})
    out: dict[str, Any] = {}
    for field, concepts in SEC_FINANCIAL_CONCEPTS.items():
        for concept in concepts:
            fact = facts.get(concept)
            if not isinstance(fact, dict):
                continue
            units = fact.get("units") or {}
            usd_values = units.get("USD") or units.get("shares") or []
            latest = _latest_fact_values(usd_values, max_items=max_items)
            if latest:
                out[field] = {
                    "concept": concept,
                    "label": fact.get("label"),
                    "values": latest,
                }
                break
    return out


def extract_sec_negative_events(
    submissions: dict[str, Any],
    *,
    cik: int,
    ticker: str,
    company_name: str,
    max_items: int = 5,
) -> list[dict[str, Any]]:
    recent = ((submissions.get("filings") or {}).get("recent") or {})
    forms = recent.get("form") or []
    items = recent.get("items") or []
    filing_dates = recent.get("filingDate") or []
    accession_numbers = recent.get("accessionNumber") or []
    primary_docs = recent.get("primaryDocument") or []
    rows: list[dict[str, Any]] = []
    for idx, form in enumerate(forms):
        form_text = str(form or "")
        if form_text != "8-K":
            continue
        item_text = str(_at(items, idx) or "")
        matched = _classify_sec_8k_items(item_text)
        if not matched:
            continue
        filing_date = _at(filing_dates, idx)
        accession = str(_at(accession_numbers, idx) or "")
        primary_doc = str(_at(primary_docs, idx) or "")
        for event in matched:
            rows.append(
                {
                    "source": "sec_submissions",
                    "url": _sec_archive_url(cik, accession, primary_doc),
                    "title": f"{company_name} ({ticker}) 8-K Item {event['item_code']}: {event['item_label']}",
                    "published_at": filing_date,
                    "fetched_at": _now_utc(),
                    "fields": ["15_events.recent_news", "sec_submissions.recent.items"],
                    "severity": event["severity"],
                    "event_type": event["event_type"],
                    "form": form_text,
                    "accession": accession,
                    "item_code": event["item_code"],
                }
            )
            if len(rows) >= max_items:
                return rows
    rows.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return rows[:max_items]


def _classify_sec_8k_items(item_text: str) -> list[dict[str, str]]:
    tokens = {token.strip() for token in item_text.replace(";", ",").split(",") if token.strip()}
    matched: list[dict[str, str]] = []
    for severity, payload in NEGATIVE_EVENT_TAXONOMY.items():
        item_map = payload.get("sec_8k_items") or {}
        for code, label in item_map.items():
            if code in tokens:
                matched.append(
                    {
                        "severity": severity,
                        "event_type": "sec_8k_item",
                        "item_code": code,
                        "item_label": str(label),
                    }
                )
    matched.sort(key=lambda item: item["severity"])
    return matched


def _sec_archive_url(cik: int, accession: str, primary_doc: str) -> str:
    if not accession or not primary_doc:
        return SEC_SUBMISSIONS_URL.format(cik=f"{cik:010d}")
    accession_path = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/{primary_doc}"


def source_plan_for(market: str, target: str) -> list[dict[str, str]]:
    if target == "missing_financials":
        if market == "US":
            return [
                {"source": "sec_companyfacts", "role": "official XBRL facts"},
                {"source": "sec_submissions", "role": "filing provenance"},
            ]
        if market == "A":
            return [
                {"source": "cninfo", "role": "official filings"},
                {"source": "exchange_filings", "role": "exchange disclosures"},
                {"source": "eastmoney_financials", "role": "field-level fallback"},
            ]
        if market == "HK":
            return [
                {"source": "hkexnews", "role": "official filings"},
                {"source": "company_ir", "role": "company published reports"},
            ]
    if target == "negative_event":
        if market == "US":
            return [
                {"source": "sec_litigation_releases", "role": "official enforcement"},
                {"source": "sec_submissions", "role": "company filed events"},
            ]
        if market == "A":
            return [
                {"source": "cninfo", "role": "company announcements"},
                {"source": "csrc", "role": "regulator enforcement"},
                {"source": "exchange_discipline", "role": "exchange discipline"},
            ]
        if market == "HK":
            return [
                {"source": "hkexnews", "role": "official announcements"},
                {"source": "sfc_enforcement", "role": "regulator enforcement"},
            ]
    return [{"source": "manual_official_source", "role": "official dated evidence required"}]


def _fetch_json(url: str, *, timeout_sec: int) -> dict[str, Any]:
    headers = {
        "User-Agent": os.environ.get("UZI_SEC_USER_AGENT", "UZI-Skill evidence overlay builder contact@example.com"),
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return json.loads(resp.read().decode(charset, errors="replace"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} from {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error from {url}: {exc.reason}") from exc


def _latest_fact_values(values: list[dict[str, Any]], *, max_items: int) -> list[dict[str, Any]]:
    clean = [item for item in values if item.get("val") is not None and item.get("filed")]
    clean.sort(key=lambda item: str(item.get("filed", "")), reverse=True)
    rows = []
    for item in clean[:max_items]:
        rows.append(
            {
                "value": item.get("val"),
                "fy": item.get("fy"),
                "fp": item.get("fp"),
                "form": item.get("form"),
                "filed": item.get("filed"),
                "accn": item.get("accn"),
            }
        )
    return rows


def _financial_fields_from_cache(ticker: str) -> dict[str, Any]:
    raw = _read_cached_raw(ticker)
    dims = raw.get("dimensions") or {}
    financials = (((dims.get("1_financials") or {}).get("data")) or {})
    if not isinstance(financials, dict):
        return {}
    fields = {}
    for key in ("roe", "roe_history", "net_margin", "gross_margin", "revenue_history"):
        value = financials.get(key)
        if value not in (None, "", [], {}):
            fields[key] = value
    return fields


def _negative_events_from_cache(ticker: str) -> list[dict[str, Any]]:
    raw = _read_cached_raw(ticker)
    dims = raw.get("dimensions") or {}
    events = (((dims.get("15_events") or {}).get("data")) or {})
    if not isinstance(events, dict):
        return []
    news = events.get("recent_news") or []
    out = []
    for item in news:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        classified = _classify_negative_text(title)
        if not classified:
            continue
        evidence = _evidence_item(
            source=str(item.get("source") or item.get("type") or "cached_news"),
            url=str(item.get("url") or ""),
            title=title,
            published_at=item.get("published_at") or item.get("date"),
            fields=["15_events.recent_news"],
        )
        evidence.update(classified)
        out.append(evidence)
    return out


def _read_cached_raw(ticker: str) -> dict[str, Any]:
    path = CACHE / ticker / "raw_data.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _has_required_financial_fields(field_mapping: dict[str, Any]) -> bool:
    merged: set[str] = set()
    for fields in field_mapping.values():
        if isinstance(fields, dict):
            merged.update(fields)
    return {"revenue", "net_income", "assets"}.issubset(merged) or {"roe", "roe_history", "net_margin"}.issubset(merged)


def _latest_filed_date(fields: dict[str, Any]) -> str | None:
    dates = []
    for payload in fields.values():
        for item in payload.get("values") or []:
            if item.get("filed"):
                dates.append(str(item["filed"]))
    return max(dates) if dates else None


def _evidence_item(
    *,
    source: str,
    url: str,
    title: str,
    published_at: Any,
    fields: list[str],
) -> dict[str, Any]:
    return {
        "source": source,
        "url": url,
        "title": title,
        "published_at": published_at,
        "fetched_at": _now_utc(),
        "fields": fields,
    }


def _finalize_confidence(overlay: dict[str, Any]) -> None:
    status = overlay["status"]
    score = {"ready": 85, "partial": 55, "gap": 20, "error": 10}.get(status, 20)
    factors = []
    if status == "ready":
        factors.append("required evidence is present and frozen")
    elif status == "partial":
        factors.append("some evidence exists but field coverage or provenance is incomplete")
    else:
        factors.append("evidence gap remains; do not infer missing facts")
    if overlay.get("errors"):
        score -= min(25, 5 * len(overlay["errors"]))
        factors.append("one or more sources failed or are not implemented")
    if overlay["target"] == "negative_event" and status != "ready":
        factors.append("negative event is not inferred from generic news or filings")
    score = max(0, min(100, score))
    level = "high" if score >= 75 else "medium" if score >= 50 else "low"
    overlay["confidence"] = {"level": level, "score": score, "factors": factors}


def _classify_negative_text(text: str) -> dict[str, str] | None:
    lowered = text.lower()
    if any(term in lowered for term in NEGATED_NEGATIVE_TERMS):
        return None
    for severity, payload in NEGATIVE_EVENT_TAXONOMY.items():
        for term in payload.get("keywords") or ():
            if str(term).lower() in lowered:
                return {
                    "severity": severity,
                    "event_type": "text_negative_event",
                    "item_code": "",
                    "item_label": str(payload["label"]),
                }
    return None


def _looks_negative(text: str) -> bool:
    return _classify_negative_text(text) is not None


def _at(values: Any, idx: int) -> Any:
    if isinstance(values, list) and 0 <= idx < len(values):
        return values[idx]
    return None


def market_for_ticker(ticker: str) -> str:
    value = ticker.upper()
    if value.startswith("HK_") or value.endswith(".HK"):
        return "HK"
    if value.endswith(".SH") or value.endswith(".SZ") or value.endswith(".BJ"):
        return "A"
    if value.endswith(".TW"):
        return "TW"
    if value.endswith(".T"):
        return "JP"
    if value.endswith(".ST") or value.endswith(".SS"):
        return "EU"
    if "." not in value and any(ch.isalpha() for ch in value):
        return "US"
    return "GLOBAL"


def _now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_overlay(overlay: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = overlay["target"]
    ticker = str(overlay["ticker"]).replace("/", "_")
    path = out_dir / f"{ticker}-{target}.json"
    path.write_text(json.dumps(overlay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen evidence overlays for branch comparison inputs.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--target", required=True, choices=SUPPORTED_TARGETS)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    overlay = build_overlay(
        args.ticker,
        args.target,
        network=not args.no_network,
        timeout_sec=args.timeout,
        max_items=args.max_items,
    )
    if not args.no_write:
        path = write_overlay(overlay, Path(args.output_dir))
        print(f"wrote {path}")
    print(
        json.dumps(
            {
                "ticker": overlay["ticker"],
                "target": overlay["target"],
                "status": overlay["status"],
                "confidence": overlay["confidence"],
                "elapsed_sec": overlay["performance"]["elapsed_sec"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if overlay["status"] in {"ready", "partial", "gap"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
