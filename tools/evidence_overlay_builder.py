from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gzip
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "uzi.evidence_overlay.v1"
DEFAULT_TIMEOUT_SEC = 12
DEFAULT_EVENT_LOOKBACK_DAYS = 730
DEFAULT_SOURCE_RECORD_LIMIT = 60
DEFAULT_HTTP_USER_AGENT = "UZI-Skill evidence-overlay/1.0"
SEC_USER_AGENT_ENV = "UZI_SEC_USER_AGENT"
SEC_REQUESTS_PER_SECOND = 8.0
SEC_REQUEST_INTERVAL_SEC = 1.0 / SEC_REQUESTS_PER_SECOND
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_LITIGATION_RELEASES_URL = "https://www.sec.gov/enforcement-litigation/litigation-releases"
SEC_TRADING_SUSPENSIONS_URL = "https://www.sec.gov/enforcement-litigation/trading-suspensions"
CNINFO_STOCK_MAP_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
CNINFO_ANNOUNCEMENTS_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_DOCUMENT_BASE_URL = "https://static.cninfo.com.cn/"
SSE_DISCIPLINE_URL = "https://query.sse.com.cn/commonSoaQuery.do"
SSE_DISCIPLINE_PAGE_URL = "https://www.sse.com.cn/regulation/supervision/measures/"
SZSE_REPORT_URL = "https://www.szse.cn/api/report/ShowReport/data"
SZSE_DISCIPLINE_PAGE_URL = "https://www.szse.cn/disclosure/supervision/measure/pushish/index.html"
SZSE_MEASURE_PAGE_URL = "https://www.szse.cn/disclosure/supervision/measure/measure/index.html"
CSRC_PENALTY_CHANNEL_ID = "28de6b87eda140cb93de4dd10d11867d"
CSRC_PENALTY_LIST_URL = (
    "https://www.csrc.gov.cn/searchList/" + CSRC_PENALTY_CHANNEL_ID
    + "?_isAgg=true&_isJson=true&_pageSize={page_size}&_template=index&_rangeTimeGte=&_channelName=&page=1"
)
HKEX_DISCIPLINE_URL = "https://www.hkex.com.hk/Listing/Disciplinary-and-Enforcement/Overview?sc_lang=en"
HKEX_CRITICAL_DOCS_URL = "https://www1.hkexnews.hk/search/predefineddoc.xhtml?predefineddocuments=9"
SFC_NEWS_SEARCH_URL = "https://apps.sfc.hk/edistributionWeb/api/news/search"
SFC_NEWS_CONTENT_URL = "https://apps.sfc.hk/edistributionWeb/api/news/content?lang=EN&refNo={ref_no}"
SFC_NEWS_DOCUMENT_URL = (
    "https://apps.sfc.hk/edistributionWeb/gateway/EN/news-and-announcements/news/doc?refNo={ref_no}"
)

OFFICIAL_EVENT_HOST_SUFFIXES = (
    "sec.gov",
    "csrc.gov.cn",
    "cninfo.com.cn",
    "sse.com.cn",
    "szse.cn",
    "hkex.com.hk",
    "hkexnews.hk",
    "sfc.hk",
)

_SEC_RATE_LOCK = threading.Lock()
_SEC_LAST_REQUEST_AT = 0.0
_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
_SEC_PLACEHOLDER_MARKERS = (
    "contact@example.com",
    "your-email@example.com",
    "example@example.com",
    "samplecompanydomain.com",
)
_SEC_PLACEHOLDER_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "test.com"}

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
        "keywords": ("sec charges", "accounting fraud", "fraud", "bankruptcy", "receivership", "财务造假", "欺诈发行"),
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
        "keywords": (
            "default",
            "delisting",
            "material impairment",
            "auditor resignation",
            "重大减值",
            "退市",
            "处罚",
            "立案",
            "公开谴责",
            "纪律处分",
        ),
    },
    "P2": {
        "label": "context-dependent operating or legal risk",
        "decision_use": "evidence for review only; not enough for automatic hard downgrade",
        "sec_8k_items": {},
        "keywords": ("lawsuit", "recall", "investigation", "诉讼", "调查", "召回"),
    },
}

NEGATED_NEGATIVE_TERMS = (
    "no fraud",
    "no violation",
    "未发现",
    "无违规",
    "不涉及处罚",
    "撤销处罚",
    "settled",
    "和解",
)

CNINFO_REPLY_TERMS = ("回复问询函", "问询函回复", "回复关注函", "关注函回复", "回复监管函", "监管函回复")
CNINFO_P0_TERMS = ("财务造假", "欺诈发行", "重大违法强制退市", "虚假财务报表")
CNINFO_P1_TERMS = (
    "行政处罚决定书",
    "行政监管措施决定书",
    "立案告知书",
    "立案调查",
    "公开谴责",
    "纪律处分",
    "警示函",
    "责令改正",
)
CNINFO_P2_TERMS = ("监管函",)

SFC_P0_TERMS = ("fraud", "false financial statements", "false accounting", "misappropriation")
SFC_P1_TERMS = (
    "commences proceedings",
    "seeks order against",
    "obtains order against",
    "reprimands",
    "fines",
    "convicted",
    "market misconduct",
    "insider dealing",
    "delisting",
)

CSRC_P0_TERMS = ("财务造假", "欺诈发行", "虚假财务报表", "重大违法强制退市")
HKEX_DOC_P0_TERMS = (
    "winding up",
    "liquidation of issuer",
    "cancellation of listing",
    "decision on cancellation of listing",
    "disclaimer of opinion",
    "adverse opinion",
)
HKEX_DOC_P1_TERMS = (
    "continued suspension",
    "resumption guidance",
    "delay in publication",
    "independent investigator",
    "internal control consultant",
)

STATUS_LABEL_ZH = {
    "ready": "证据已冻结",
    "partial": "证据不完整",
    "gap": "证据缺口",
    "error": "证据错误",
}

TARGET_LABEL_ZH = {
    "missing_financials": "财务字段补证据",
    "negative_event": "负面事件证据",
}

CONFIDENCE_LABEL_ZH = {
    "high": "高",
    "medium": "中",
    "low": "低",
}

SEVERITY_LABEL_ZH = {
    "P0": "P0 硬风险",
    "P1": "P1 重大风险升级",
    "P2": "P2 上下文风险",
}

FACTOR_LABEL_ZH = {
    "required evidence is present and frozen": "必要证据已存在并冻结",
    "some evidence exists but field coverage or provenance is incomplete": "已有部分证据，但字段覆盖或来源追溯不完整",
    "evidence gap remains; do not infer missing facts": "仍存在证据缺口，不能推断缺失事实",
    "one or more sources failed or are not implemented": "一个或多个来源失败或尚未实现",
    "negative event is not inferred from generic news or filings": "负面事件不能从泛新闻或普通披露中推断",
}


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
    network: bool = False,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
    lookback_days: int = DEFAULT_EVENT_LOOKBACK_DAYS,
    source_record_limit: int = DEFAULT_SOURCE_RECORD_LIMIT,
    as_of: str | None = None,
) -> dict[str, Any]:
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported target: {target}")
    started = time.perf_counter()
    market = market_for_ticker(ticker)
    if market == "US" and network:
        # Configuration errors must not be downgraded into an ordinary evidence
        # gap: reject them before cache inspection or any adapter can run.
        _declared_sec_user_agent()
    as_of_date = _parse_iso_date(as_of) if as_of else dt.date.today()
    if lookback_days < 1:
        raise ValueError("lookback_days must be positive")
    if source_record_limit < 1:
        raise ValueError("source_record_limit must be positive")
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
        "source_coverage": [],
        "errors": [],
        "fetched_at": _now_utc(),
        "as_of": as_of_date.isoformat(),
        "lookback_days": lookback_days,
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
        _fill_negative_event_overlay(
            overlay,
            network=network,
            timeout_sec=timeout_sec,
            max_items=max_items,
            lookback_days=lookback_days,
            source_record_limit=source_record_limit,
            as_of=as_of_date,
        )

    overlay["performance"]["elapsed_sec"] = round(time.perf_counter() - started, 3)
    _finalize_confidence(overlay)
    _attach_display_labels(overlay)
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
    lookback_days: int,
    source_record_limit: int,
    as_of: dt.date,
) -> None:
    ticker = overlay["ticker"]
    market = overlay["market"]
    overlay["lifecycle"] = {
        "status": "not_evaluated",
        "links": [],
        "policy": [
            "resolution requires a later exact-issuer official record",
            "resolution must match the same narrow event family and rule topic",
            "penalties, fraud, non-reliance and generic remediation stay unresolved",
        ],
    }
    cache_events = _negative_events_from_cache(ticker)
    if cache_events:
        overlay["field_mapping"]["cache_events"] = {"events": cache_events}
        overlay["evidence"].extend(cache_events)

    if market == "US" and network:
        _collect_us_negative_events(
            overlay,
            timeout_sec=timeout_sec,
            max_items=max_items,
            lookback_days=lookback_days,
            as_of=as_of,
        )
    elif market == "A" and network:
        _collect_a_share_negative_events(
            overlay,
            timeout_sec=timeout_sec,
            max_items=max_items,
            lookback_days=lookback_days,
            source_record_limit=source_record_limit,
            as_of=as_of,
        )
    elif market == "HK" and network:
        _collect_hk_negative_events(
            overlay,
            timeout_sec=timeout_sec,
            max_items=max_items,
            lookback_days=lookback_days,
            source_record_limit=source_record_limit,
            as_of=as_of,
        )
    elif market == "US" and not network:
        for source in ("sec_submissions", "sec_litigation_releases", "sec_trading_suspensions"):
            _record_source_error(overlay, source, "network disabled")
    elif market in {"A", "HK"} and not network:
        for source in (
            ("cninfo", "csrc_penalties", "exchange_discipline")
            if market == "A"
            else ("hkex_discipline", "hkex_critical_filings", "sfc_enforcement")
        ):
            _record_source_error(overlay, source, "network disabled")
    elif network:
        overlay["errors"].append(
            {
                "source": "negative_event_online",
                "error": f"no implemented official negative-event adapter for market {market}",
            }
        )
    else:
        overlay["errors"].append({"source": "negative_event_online", "error": "network disabled"})

    overlay["evidence"] = _finalize_negative_events(
        overlay["evidence"],
        as_of=as_of,
        lookback_days=lookback_days,
        max_items=max_items,
    )
    _reconcile_source_coverage(overlay)
    traceable_events = [
        item
        for item in overlay["evidence"]
        if item.get("url")
        and item.get("title")
        and item.get("official_source") is True
        and item.get("entity_match") == "exact"
        and item.get("severity") in {"P0", "P1", "P2"}
    ]
    if any(item.get("severity") in {"P0", "P1"} for item in traceable_events):
        overlay["status"] = "ready"
    elif traceable_events:
        overlay["status"] = "partial"
    else:
        overlay["status"] = "gap"


def _collect_us_negative_events(
    overlay: dict[str, Any],
    *,
    timeout_sec: int,
    max_items: int,
    lookback_days: int,
    as_of: dt.date,
) -> None:
    ticker = str(overlay["ticker"])
    try:
        cik, company_name = sec_cik_for_ticker(ticker, timeout_sec=timeout_sec)
    except Exception as exc:  # noqa: BLE001 - all US official adapters depend on exact SEC identity
        for source in ("sec_submissions", "sec_litigation_releases", "sec_trading_suspensions"):
            _record_source_error(overlay, source, exc)
        return

    try:
        events = extract_sec_negative_events(
            fetch_sec_submissions(cik, timeout_sec=timeout_sec),
            cik=cik,
            ticker=ticker,
            company_name=company_name,
            # A resolving 3.01 filing is removed from negative evidence after
            # content review, so scan beyond the display limit first.
            max_items=max(max_items * 2, max_items + 3),
        )
        events, links, lifecycle_scanned, lifecycle_errors = enrich_sec_listing_lifecycle(
            events,
            timeout_sec=timeout_sec,
            lookback_days=lookback_days,
            as_of=as_of,
        )
        overlay["lifecycle"]["links"].extend(links)
        overlay["lifecycle"]["status"] = (
            "linked" if links else "partial" if lifecycle_errors else "no_match"
        )
        overlay["lifecycle"]["scanned"] = lifecycle_scanned
        if lifecycle_errors:
            overlay["lifecycle"]["errors"] = lifecycle_errors
        _add_adapter_events(overlay, "sec_submissions", events)
        _record_source_coverage(
            overlay,
            "sec_submissions",
            "partial" if lifecycle_errors else "ok",
            matched=len(events),
            scanned=1,
        )
    except Exception as exc:  # noqa: BLE001 - other authority layers remain usable
        _record_source_error(overlay, "sec_submissions", exc)

    adapters: list[tuple[str, Any]] = [
        (
            "sec_litigation_releases",
            lambda: fetch_sec_release_negative_events(
                ticker,
                company_name=company_name,
                page_url=SEC_LITIGATION_RELEASES_URL,
                severity="P1",
                event_type="sec_litigation_release",
                timeout_sec=timeout_sec,
                max_items=max_items,
            ),
        ),
        (
            "sec_trading_suspensions",
            lambda: fetch_sec_release_negative_events(
                ticker,
                company_name=company_name,
                page_url=SEC_TRADING_SUSPENSIONS_URL,
                severity="P0",
                event_type="sec_trading_suspension",
                timeout_sec=timeout_sec,
                max_items=max_items,
            ),
        ),
    ]
    for source, adapter in adapters:
        try:
            events, scanned = adapter()
            _add_adapter_events(overlay, source, events)
            _record_source_coverage(overlay, source, "ok", matched=len(events), scanned=scanned)
        except Exception as exc:  # noqa: BLE001 - one official source cannot suppress the others
            _record_source_error(overlay, source, exc)


def _collect_a_share_negative_events(
    overlay: dict[str, Any],
    *,
    timeout_sec: int,
    max_items: int,
    lookback_days: int,
    source_record_limit: int,
    as_of: dt.date,
) -> None:
    ticker = str(overlay["ticker"])
    adapters: list[tuple[str, Any]] = [
        (
            "cninfo",
            lambda: fetch_cninfo_negative_events(
                ticker,
                timeout_sec=timeout_sec,
                max_items=max_items,
                lookback_days=lookback_days,
                source_record_limit=source_record_limit,
                as_of=as_of,
            ),
        ),
        (
            "csrc_penalties",
            lambda: fetch_csrc_negative_events(
                ticker,
                timeout_sec=timeout_sec,
                max_items=max_items,
                lookback_days=lookback_days,
                source_record_limit=source_record_limit,
                as_of=as_of,
            ),
        ),
    ]
    upper = ticker.upper()
    if upper.endswith(".SH"):
        adapters.append(
            (
                "sse_discipline",
                lambda: fetch_sse_negative_events(ticker, timeout_sec=timeout_sec, max_items=max_items),
            )
        )
    elif upper.endswith(".SZ"):
        adapters.append(
            (
                "szse_discipline",
                lambda: fetch_szse_negative_events(
                    ticker,
                    timeout_sec=timeout_sec,
                    max_items=max_items,
                    lookback_days=lookback_days,
                    as_of=as_of,
                ),
            )
        )
    else:
        _record_source_error(overlay, "exchange_discipline", f"unsupported A-share exchange suffix: {ticker}")

    for source, adapter in adapters:
        try:
            result = adapter()
            events, scanned = result[:2]
            failed = int(result[2]) if len(result) > 2 else 0
            _add_adapter_events(overlay, source, events)
            status = "partial" if failed else "ok"
            _record_source_coverage(
                overlay,
                source,
                status,
                matched=len(events),
                scanned=scanned,
                failed=failed,
            )
            if failed:
                overlay["errors"].append(
                    {"source": source, "error": f"{failed} source records failed; usable records were preserved"}
                )
        except Exception as exc:  # noqa: BLE001 - each official source fails independently
            _record_source_error(overlay, source, exc)


def _collect_hk_negative_events(
    overlay: dict[str, Any],
    *,
    timeout_sec: int,
    max_items: int,
    lookback_days: int,
    source_record_limit: int,
    as_of: dt.date,
) -> None:
    ticker = str(overlay["ticker"])
    adapters: list[tuple[str, Any]] = [
        (
            "hkex_discipline",
            lambda: fetch_hkex_negative_events(ticker, timeout_sec=timeout_sec, max_items=max_items),
        ),
        (
            "hkex_critical_filings",
            lambda: fetch_hkex_critical_filing_events(
                ticker,
                timeout_sec=timeout_sec,
                max_items=max_items,
            ),
        ),
        (
            "sfc_enforcement",
            lambda: fetch_sfc_negative_events(
                ticker,
                timeout_sec=timeout_sec,
                max_items=max_items,
                lookback_days=lookback_days,
                source_record_limit=source_record_limit,
                as_of=as_of,
            ),
        ),
    ]
    for source, adapter in adapters:
        try:
            result = adapter()
            events, scanned = result[:2]
            failed = int(result[2]) if len(result) > 2 else 0
            _add_adapter_events(overlay, source, events)
            status = "partial" if failed else "ok"
            _record_source_coverage(
                overlay,
                source,
                status,
                matched=len(events),
                scanned=scanned,
                failed=failed,
            )
            if failed:
                overlay["errors"].append(
                    {"source": source, "error": f"{failed} source records failed; usable records were preserved"}
                )
        except Exception as exc:  # noqa: BLE001 - each official source fails independently
            _record_source_error(overlay, source, exc)


def fetch_cninfo_negative_events(
    ticker: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
    lookback_days: int = DEFAULT_EVENT_LOOKBACK_DAYS,
    source_record_limit: int = DEFAULT_SOURCE_RECORD_LIMIT,
    as_of: dt.date | None = None,
) -> tuple[list[dict[str, Any]], int]:
    code = _a_share_code(ticker)
    as_of = as_of or dt.date.today()
    mapping = _fetch_json(CNINFO_STOCK_MAP_URL, timeout_sec=timeout_sec)
    identity = next((row for row in mapping.get("stockList") or [] if str(row.get("code")) == code), None)
    if not identity or not identity.get("orgId"):
        raise ValueError(f"CNINFO orgId mapping not found for {ticker}")
    is_sh = ticker.upper().endswith(".SH")
    body = urllib.parse.urlencode(
        {
            "pageNum": "1",
            "pageSize": str(min(100, source_record_limit)),
            "column": "sse" if is_sh else "szse",
            "tabName": "fulltext",
            "plate": "sh" if is_sh else "sz",
            "stock": f"{code},{identity['orgId']}",
            "searchkey": "",
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": f"{(as_of - dt.timedelta(days=lookback_days)).isoformat()}~{as_of.isoformat()}",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
    ).encode("utf-8")
    payload = _fetch_json_request(
        CNINFO_ANNOUNCEMENTS_URL,
        timeout_sec=timeout_sec,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://www.cninfo.com.cn/",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    rows = payload.get("announcements") or []
    events: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("secCode") or "").zfill(6) != code:
            continue
        title = html.unescape(str(row.get("announcementTitle") or "")).strip()
        classified = classify_cninfo_title(title)
        if not classified:
            continue
        adjunct = str(row.get("adjunctUrl") or "").lstrip("/")
        if not adjunct:
            continue
        events.append(
            _official_event_item(
                source="cninfo_company_announcement",
                url=urllib.parse.urljoin(CNINFO_DOCUMENT_BASE_URL, adjunct),
                title=title,
                published_at=_timestamp_ms_to_date(row.get("announcementTime")),
                severity=classified["severity"],
                event_type=classified["event_type"],
                entity_scope="issuer",
                match_method="secCode+orgId",
                source_record_id=str(row.get("announcementId") or adjunct),
            )
        )
        if len(events) >= max_items:
            break
    return events, len(rows)


def classify_cninfo_title(title: str) -> dict[str, str] | None:
    compact = re.sub(r"\s+", "", html.unescape(title))
    if not compact or any(term in compact for term in CNINFO_REPLY_TERMS):
        return None
    if "问询函" in compact or "关注函" in compact:
        return None
    if any(term in compact for term in CNINFO_P0_TERMS):
        return {"severity": "P0", "event_type": "cninfo_severe_enforcement"}
    if any(term in compact for term in CNINFO_P1_TERMS):
        return {"severity": "P1", "event_type": "cninfo_enforcement_disclosure"}
    if any(term in compact for term in CNINFO_P2_TERMS):
        return {"severity": "P2", "event_type": "cninfo_regulatory_letter"}
    return None


def fetch_csrc_negative_events(
    ticker: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
    lookback_days: int = DEFAULT_EVENT_LOOKBACK_DAYS,
    source_record_limit: int = DEFAULT_SOURCE_RECORD_LIMIT,
    as_of: dt.date | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    code = _a_share_code(ticker)
    as_of = as_of or dt.date.today()
    mapping = _fetch_json(CNINFO_STOCK_MAP_URL, timeout_sec=timeout_sec)
    identity = next((row for row in mapping.get("stockList") or [] if str(row.get("code")) == code), None)
    if not identity:
        raise ValueError(f"CNINFO identity mapping not found for CSRC match: {ticker}")
    short_name = str(identity.get("zwjc") or "").strip()
    # The CSRC channel is authority-wide. Bound the body scan so evidence
    # freezing remains a preprocessing step rather than an unbounded crawler.
    page_size = min(30, max(1, source_record_limit))
    payload = _fetch_json(
        CSRC_PENALTY_LIST_URL.format(page_size=page_size),
        timeout_sec=timeout_sec,
        headers={"Referer": "https://www.csrc.gov.cn/csrc/c101928/common_list.shtml"},
    )
    rows = ((payload.get("data") or {}).get("results") or [])[:page_size]
    lower_date = as_of - dt.timedelta(days=lookback_days)
    eligible = []
    for row in rows:
        published = _coerce_date(row.get("publishedTimeStr"))
        if published and lower_date <= published <= as_of and row.get("url"):
            eligible.append((row, published))

    def fetch_one(item: tuple[dict[str, Any], dt.date]) -> tuple[dict[str, Any] | None, bool]:
        row, published = item
        try:
            url = urllib.parse.urljoin("https://www.csrc.gov.cn/", str(row.get("url")))
            body = _strip_html(_fetch_text(url, timeout_sec=timeout_sec))
            classified = classify_csrc_penalty(body, code=code, short_name=short_name)
            if not classified:
                return None, False
            title = html.unescape(str(row.get("title") or "中国证监会行政处罚决定书")).strip()
            return (
                _official_event_item(
                    source="csrc_penalty_decision",
                    url=url,
                    title=f"{title}：{short_name or code}",
                    published_at=published.isoformat(),
                    severity=classified["severity"],
                    event_type=classified["event_type"],
                    entity_scope="issuer",
                    match_method=classified["match_method"],
                    source_record_id=url,
                ),
                False,
            )
        except Exception:  # noqa: BLE001 - retain usable decisions if one article fails
            return None, True

    events: list[dict[str, Any]] = []
    failed = 0
    workers = min(6, max(1, len(eligible)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for event, did_fail in executor.map(fetch_one, eligible):
            failed += int(did_fail)
            if event:
                events.append(event)
    events.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return events[:max_items], len(rows), failed


def classify_csrc_penalty(text: str, *, code: str, short_name: str) -> dict[str, str] | None:
    plain = re.sub(r"\s+", "", html.unescape(text))
    if "行政处罚" not in plain or "当事人" not in plain:
        return None
    respondent = plain[plain.find("当事人") : plain.find("当事人") + 800]
    for marker in ("依据", "经查", "案情", "本案"):
        marker_pos = respondent.find(marker)
        if marker_pos > 0:
            respondent = respondent[:marker_pos]
    base_name = re.sub(r"^(?:\*?ST|SST)", "", short_name, flags=re.IGNORECASE)
    aliases = {value for value in (short_name, base_name, base_name + "股份") if len(value) >= 2}
    code_match = bool(re.search(rf"(?<!\d){re.escape(code)}(?!\d)", respondent))
    alias_match = any(alias and alias in respondent for alias in aliases)
    if not code_match and not alias_match:
        return None
    severity = "P0" if any(term in plain for term in CSRC_P0_TERMS) else "P1"
    return {
        "severity": severity,
        "event_type": "csrc_severe_issuer_penalty" if severity == "P0" else "csrc_issuer_penalty",
        "match_method": "respondent_stock_code" if code_match else "respondent_exact_stock_alias",
    }


def fetch_sse_negative_events(
    ticker: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
) -> tuple[list[dict[str, Any]], int]:
    code = _a_share_code(ticker)
    params = {
        "isPagination": "true",
        "pageHelp.pageSize": "50",
        "pageHelp.pageNo": "1",
        "pageHelp.beginPage": "1",
        "pageHelp.cacheSize": "1",
        "pageHelp.endPage": "1",
        "sqlId": "BS_KCB_GGLL_NEW",
        "siteId": "28",
        "channelId": "10007,10008,10009,10010",
        "type": "",
        "stockcode": code,
        "extTeacher": "",
        "extWTFL": "",
        "createTime": "",
        "createTimeEnd": "",
        "order": "createTime|desc,stockcode|asc",
    }
    payload = _fetch_json(
        f"{SSE_DISCIPLINE_URL}?{urllib.parse.urlencode(params)}",
        timeout_sec=timeout_sec,
        headers={"Referer": SSE_DISCIPLINE_PAGE_URL},
    )
    rows = payload.get("result") or (payload.get("pageHelp") or {}).get("data") or []
    events: list[dict[str, Any]] = []
    for row in rows:
        row_code = str(row.get("extSECURITY_CODE") or row.get("stockcode") or "").zfill(6)
        if row_code != code:
            continue
        classified = classify_sse_action(str(row.get("extWTFL") or row.get("extTYPE") or ""))
        if not classified:
            continue
        raw_url = str(row.get("docURL") or "").strip()
        if raw_url and not raw_url.startswith(("http://", "https://")):
            raw_url = "https://" + raw_url.lstrip("/")
        events.append(
            _official_event_item(
                source="sse_discipline",
                url=raw_url,
                title=str(row.get("docTitle") or "").strip(),
                published_at=str(row.get("createTime") or "")[:10],
                severity=classified["severity"],
                event_type=classified["event_type"],
                entity_scope="issuer" if str(row.get("extDWDM")) == "0" else "related_person",
                match_method="extSECURITY_CODE",
                source_record_id=str(row.get("docId") or raw_url),
            )
        )
        if len(events) >= max_items:
            break
    return events, len(rows)


def classify_sse_action(action: str) -> dict[str, str] | None:
    compact = re.sub(r"\s+", "", action)
    if any(term in compact for term in ("公开谴责", "通报批评", "公开认定")):
        return {"severity": "P1", "event_type": "sse_disciplinary_action"}
    if any(term in compact for term in ("监管警示", "监管关注")):
        return {"severity": "P2", "event_type": "sse_regulatory_measure"}
    return None


def fetch_szse_negative_events(
    ticker: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
    lookback_days: int = DEFAULT_EVENT_LOOKBACK_DAYS,
    as_of: dt.date | None = None,
) -> tuple[list[dict[str, Any]], int]:
    code = _a_share_code(ticker)
    as_of = as_of or dt.date.today()
    start = (as_of - dt.timedelta(days=lookback_days)).isoformat()
    specs = (
        (
            "1800_jgxxgk_cf",
            "tab2",
            SZSE_DISCIPLINE_PAGE_URL,
            {"selectGsbk": "0", "txtBj": "", "txtDMorJC": code, "selectCflb": "", "txtStartDate": start, "txtEndDate": as_of.isoformat()},
            "discipline",
        ),
        (
            "1800_jgxxgk",
            "tab1",
            SZSE_MEASURE_PAGE_URL,
            {"txtZqdm": code, "selectBkmc": "0", "txtjgsy": "", "txtDate": start, "txtEnd": as_of.isoformat()},
            "measure",
        ),
    )
    events: list[dict[str, Any]] = []
    scanned = 0
    for catalog, tab, referer, query, kind in specs:
        params = {"SHOWTYPE": "JSON", "CATALOGID": catalog, "TABKEY": tab, "PAGENO": "1", **query}
        payload = _fetch_json(
            f"{SZSE_REPORT_URL}?{urllib.parse.urlencode(params)}",
            timeout_sec=timeout_sec,
            headers={"Referer": referer},
        )
        block = payload[0] if isinstance(payload, list) and payload else {}
        rows = block.get("data") or []
        scanned += len(rows)
        for row in rows:
            event = _szse_row_to_event(row, code=code, kind=kind)
            if event:
                events.append(event)
    events.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return events[:max_items], scanned


def _szse_row_to_event(row: dict[str, Any], *, code: str, kind: str) -> dict[str, Any] | None:
    row_code = str(row.get("xx_gsdm") or row.get("gkxx_gsdm") or "").zfill(6)
    if row_code != code:
        return None
    if kind == "discipline":
        title = str(row.get("xx_bt") or "").strip()
        action = str(row.get("xx_cflb") or "").strip()
        issuer_named = "股份有限公司" in title or "上市公司" in title
        severity = "P1" if issuer_named else "P2"
        event_type = "szse_disciplinary_action" if issuer_named else "szse_related_person_discipline"
        published_at = row.get("xx_fwrq")
        link_html = str(row.get("ck") or "")
        entity_scope = "issuer" if issuer_named else "related_person"
    else:
        title = f"深圳证券交易所{row.get('gkxx_jgcs') or '监管措施'}：{row.get('gkxx_gsjc') or code}"
        action = str(row.get("gkxx_jgcs") or "").strip()
        if "监管函" not in action and "警示" not in action:
            return None
        severity = "P2"
        event_type = "szse_regulatory_measure"
        published_at = row.get("gkxx_gdrq")
        link_html = str(row.get("hjnr") or "")
        entity_scope = "issuer" if "上市公司" in str(row.get("gkxx_sjdx") or "") else "related_person"
    path_match = re.search(r"encode-open=['\"]([^'\"]+)", html.unescape(link_html), flags=re.IGNORECASE)
    if not path_match:
        return None
    path = path_match.group(1).strip()
    url = urllib.parse.urljoin("https://www.szse.cn/", path)
    return _official_event_item(
        source="szse_discipline" if kind == "discipline" else "szse_regulatory_measure",
        url=url,
        title=title or action,
        published_at=published_at,
        severity=severity,
        event_type=event_type,
        entity_scope=entity_scope,
        match_method="exchange_company_code",
        source_record_id=path,
    )


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href.strip(), re.sub(r"\s+", " ", " ".join(self._text)).strip()))
            self._href = None
            self._text = []


def fetch_hkex_negative_events(
    ticker: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
) -> tuple[list[dict[str, Any]], int]:
    page = _fetch_text(HKEX_DISCIPLINE_URL, timeout_sec=timeout_sec)
    return extract_hkex_negative_events(page, ticker=ticker, max_items=max_items)


def extract_hkex_negative_events(
    page: str,
    *,
    ticker: str,
    max_items: int = 5,
) -> tuple[list[dict[str, Any]], int]:
    target_code = _hk_numeric_code(ticker)
    parser = _AnchorCollector()
    parser.feed(page)
    relevant = [(href, title) for href, title in parser.anchors if "Stock Code:" in title]
    events: list[dict[str, Any]] = []
    for href, title in relevant:
        code_match = re.search(r"Stock Code:\s*0*(\d+)\s*\)", title, flags=re.IGNORECASE)
        if not code_match or str(int(code_match.group(1))) != target_code:
            continue
        related_only = bool(re.search(r"against\s+(?:a\s+)?(?:former\s+)?director\s+of", title, flags=re.IGNORECASE))
        published_at = _date_from_hkex_url(href)
        events.append(
            _official_event_item(
                source="hkex_disciplinary_action",
                url=urllib.parse.urljoin(HKEX_DISCIPLINE_URL, href),
                title=title,
                published_at=published_at,
                severity="P2" if related_only else "P1",
                event_type="hkex_related_person_discipline" if related_only else "hkex_issuer_discipline",
                entity_scope="related_person" if related_only else "issuer",
                match_method="title_stock_code",
                source_record_id=href,
            )
        )
        if len(events) >= max_items:
            break
    return events, len(relevant)


def fetch_hkex_critical_filing_events(
    ticker: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
) -> tuple[list[dict[str, Any]], int]:
    page = _fetch_text(HKEX_CRITICAL_DOCS_URL, timeout_sec=timeout_sec)
    return extract_hkex_critical_filing_events(page, ticker=ticker, max_items=max_items)


def extract_hkex_critical_filing_events(
    page: str,
    *,
    ticker: str,
    max_items: int = 5,
) -> tuple[list[dict[str, Any]], int]:
    target = _hk_numeric_code(ticker)
    rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, flags=re.IGNORECASE | re.DOTALL)
    events: list[dict[str, Any]] = []
    scanned = 0
    for row in rows:
        code_match = re.search(
            r"stock-short-code[^>]*>.*?Stock Code:\s*</span>\s*0*(\d+)",
            row,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not code_match:
            continue
        scanned += 1
        if str(int(code_match.group(1))) != target:
            continue
        date_match = re.search(r"release-time[^>]*>.*?(\d{2}/\d{2}/\d{4})", row, flags=re.IGNORECASE | re.DOTALL)
        link_match = re.search(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", row, flags=re.IGNORECASE | re.DOTALL)
        headline_match = re.search(r"<div\s+class=[\"']headline[\"']>(.*?)</div>", row, flags=re.IGNORECASE | re.DOTALL)
        if not date_match or not link_match:
            continue
        title = _strip_html(link_match.group(2)).strip()
        headline = _strip_html(headline_match.group(1)).strip() if headline_match else ""
        classified = classify_hkex_critical_filing(f"{headline} {title}")
        if not classified:
            continue
        published = dt.datetime.strptime(date_match.group(1), "%d/%m/%Y").date().isoformat()
        href = html.unescape(link_match.group(1)).strip()
        events.append(
            _official_event_item(
                source="hkex_issuer_critical_filing",
                url=urllib.parse.urljoin(HKEX_CRITICAL_DOCS_URL, href),
                title=title,
                published_at=published,
                severity=classified["severity"],
                event_type=classified["event_type"],
                entity_scope="issuer",
                match_method="predefined_document_stock_code",
                source_record_id=href,
            )
        )
        if len(events) >= max_items:
            break
    return events, scanned


def classify_hkex_critical_filing(text: str) -> dict[str, str] | None:
    lowered = re.sub(r"\s+", " ", html.unescape(text)).lower()
    if "resumption" in lowered and not any(term in lowered for term in ("continued suspension", "resumption guidance")):
        return None
    if any(term in lowered for term in HKEX_DOC_P0_TERMS):
        return {"severity": "P0", "event_type": "hkex_issuer_hard_risk_filing"}
    if any(term in lowered for term in HKEX_DOC_P1_TERMS):
        return {"severity": "P1", "event_type": "hkex_issuer_suspension_risk"}
    # A bare halt can precede routine announcements and is not a negative fact.
    return None


def fetch_sfc_negative_events(
    ticker: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
    lookback_days: int = DEFAULT_EVENT_LOOKBACK_DAYS,
    source_record_limit: int = DEFAULT_SOURCE_RECORD_LIMIT,
    as_of: dt.date | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    target_code = _hk_numeric_code(ticker)
    as_of = as_of or dt.date.today()
    start_year = (as_of - dt.timedelta(days=lookback_days)).year
    records: list[dict[str, Any]] = []
    for year in range(as_of.year, start_year - 1, -1):
        page_no = 0
        while len(records) < source_record_limit:
            query = {
                "lang": "EN",
                "category": "enforcement",
                "year": str(year),
                "month": "all",
                "pageNo": page_no,
                "pageSize": 20,
                "isLoading": True,
                "errors": None,
                "items": None,
                "total": -1,
            }
            payload = _post_json(SFC_NEWS_SEARCH_URL, query, timeout_sec=timeout_sec)
            items = payload.get("items") or []
            records.extend(items[: max(0, source_record_limit - len(records))])
            if not items or (page_no + 1) * 20 >= int(payload.get("total") or 0):
                break
            page_no += 1
        if len(records) >= source_record_limit:
            break

    def fetch_one(record: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
        try:
            ref_no = str(record.get("newsRefNo") or "").strip()
            if not ref_no:
                return None, False
            content = _fetch_json(
                SFC_NEWS_CONTENT_URL.format(ref_no=urllib.parse.quote(ref_no)), timeout_sec=timeout_sec
            )
            plain = _strip_html(str(content.get("html") or ""))
            contexts = _sfc_stock_code_contexts(plain, target_code)
            if not contexts:
                return None, False
            title = html.unescape(str(content.get("title") or record.get("title") or "")).strip()
            company_tokens = _sfc_company_tokens(title)
            if company_tokens and not any(
                any(token in context.lower() for token in company_tokens) for context in contexts
            ):
                return None, False
            classified = classify_sfc_enforcement(title, plain)
            if not classified:
                return None, False
            return (
                _official_event_item(
                    source="sfc_enforcement",
                    url=SFC_NEWS_DOCUMENT_URL.format(ref_no=urllib.parse.quote(ref_no)),
                    title=title,
                    published_at=str(record.get("issueDate") or "")[:10],
                    severity=classified["severity"],
                    event_type=classified["event_type"],
                    entity_scope=classified["entity_scope"],
                    match_method="body_stock_code+title_company_context",
                    source_record_id=ref_no,
                ),
                False,
            )
        except Exception:  # noqa: BLE001 - one bad SFC article must not discard the entire frozen source batch
            return None, True

    events: list[dict[str, Any]] = []
    failed = 0
    workers = min(6, max(1, len(records)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for event, did_fail in executor.map(fetch_one, records):
            failed += int(did_fail)
            if event:
                events.append(event)
    events.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return events[:max_items], len(records), failed


def _extract_sfc_stock_codes(text: str) -> set[str]:
    return {str(int(value)) for value in re.findall(r"stock\s+code\s*[:：]\s*0*(\d+)", text, flags=re.IGNORECASE)}


def _sfc_stock_code_contexts(text: str, target_code: str) -> list[str]:
    contexts = []
    pattern = re.compile(r"stock\s+code\s*[:：]\s*0*(\d+)", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        if str(int(match.group(1))) == target_code:
            contexts.append(text[max(0, match.start() - 240) : min(len(text), match.end() + 120)])
    return contexts


def _sfc_company_tokens(title: str) -> set[str]:
    stop = {
        "against",
        "chairman",
        "chief",
        "commences",
        "company",
        "director",
        "enforcement",
        "former",
        "group",
        "holdings",
        "limited",
        "obtains",
        "order",
        "proceedings",
        "seeks",
        "share",
        "sfc",
    }
    return {word for word in re.findall(r"[a-z]{4,}", title.lower()) if word not in stop}


def classify_sfc_enforcement(title: str, body: str) -> dict[str, str] | None:
    lowered_title = title.lower()
    lowered = f"{title} {body}".lower()
    related_only = bool(
        re.search(r"\bformer\s+(?:chairman|director|chief executive|officer)\b", lowered_title)
        or re.search(r"\bdirector\s+of\b", lowered_title)
    )
    if related_only:
        return {"severity": "P2", "event_type": "sfc_related_person_enforcement", "entity_scope": "related_person"}
    issuer_named = any(term in lowered_title for term in (" limited", " holdings", " company", " corporation"))
    if issuer_named and any(term in lowered for term in SFC_P0_TERMS):
        return {"severity": "P0", "event_type": "sfc_severe_issuer_enforcement", "entity_scope": "issuer"}
    if issuer_named and any(term in lowered for term in SFC_P1_TERMS):
        return {"severity": "P1", "event_type": "sfc_issuer_enforcement", "entity_scope": "issuer"}
    return None


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


def fetch_sec_release_negative_events(
    ticker: str,
    *,
    company_name: str,
    page_url: str,
    severity: str,
    event_type: str,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    max_items: int = 5,
) -> tuple[list[dict[str, Any]], int]:
    page = _fetch_text(page_url, timeout_sec=timeout_sec)
    rows = extract_sec_release_rows(page)
    events: list[dict[str, Any]] = []
    for row in rows:
        if not _sec_respondent_matches_company(str(row.get("respondents") or ""), company_name):
            continue
        events.append(
            _official_event_item(
                source=event_type,
                url=urllib.parse.urljoin(page_url, str(row.get("url") or "")),
                title=f"{row.get('respondents')} ({ticker})",
                published_at=row.get("published_at"),
                severity=severity,
                event_type=event_type,
                entity_scope="issuer",
                match_method="SEC exact registrant name",
                source_record_id=str(row.get("release_no") or row.get("url") or ""),
            )
        )
        if len(events) >= max_items:
            break
    return events, len(rows)


def extract_sec_release_rows(page: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for block in re.findall(
        r"<tr\b[^>]*class=[\"'][^\"']*pr-list-page-row[^\"']*[\"'][^>]*>(.*?)</tr>",
        page,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        date_match = re.search(
            r"<time\b[^>]*datetime=[\"']([^\"']+)[\"'][^>]*>(.*?)</time>",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        respondent_match = re.search(
            r"release-view__respondents[^>]*>\s*<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not date_match or not respondent_match:
            continue
        release_match = re.search(r"Release No\.?</span>\s*<span[^>]*>([^<]+)", block, flags=re.IGNORECASE)
        displayed_date = _strip_html(date_match.group(2)).strip()
        try:
            published_at = dt.datetime.strptime(displayed_date, "%B %d, %Y").date().isoformat()
        except ValueError:
            published_at = date_match.group(1)[:10]
        rows.append(
            {
                "published_at": published_at,
                "url": html.unescape(respondent_match.group(1)).strip(),
                "respondents": _strip_html(respondent_match.group(2)).strip(),
                "release_no": _strip_html(release_match.group(1)).strip() if release_match else "",
            }
        )
    return rows


def _normalized_sec_entity(value: str) -> str:
    lowered = html.unescape(value).lower().replace("&", " and ")
    lowered = re.sub(r"\b(incorporated|inc|corp|corporation|company|co|limited|ltd|plc|llc)\b", " ", lowered)
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _sec_respondent_matches_company(respondents: str, company_name: str) -> bool:
    target = _normalized_sec_entity(company_name)
    if len(target) < 5:
        return False
    candidates = re.split(r"\s*;\s*|\s+et\s+al\.?|\s+and\s+(?=[A-Z])", respondents)
    normalized = [_normalized_sec_entity(item) for item in candidates]
    return any(item == target or item.startswith(target + " ") for item in normalized)


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
                    "official_source": True,
                    "entity_match": "exact",
                    "entity_scope": "issuer",
                    "match_method": "SEC CIK+ticker",
                    "source_record_id": accession,
                    "canonical_event_id": f"sec_submissions:{accession}",
                    "resolution_status": "unknown",
                }
            )
            if len(rows) >= max_items:
                return rows
    rows.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    return rows[:max_items]


def classify_sec_listing_lifecycle(text: str) -> dict[str, str] | None:
    """Classify only high-precision Nasdaq periodic-report compliance lifecycle text.

    Item 3.01 covers many unrelated listing rules.  We intentionally support
    only Rule 5250(c)(1), where a later issuer filing can explicitly say the
    company now complies and the matter is closed.  Extensions, plans and
    expected future compliance are not resolutions.
    """
    normalized = re.sub(r"\s+", " ", html.unescape(text)).lower()
    if "5250(c)(1)" not in normalized:
        return None
    topic = "nasdaq_periodic_reporting_rule_5250_c_1"
    lifecycle_key = "sec:nasdaq:5250(c)(1):periodic_reporting"
    resolved = (
        "now complies with nasdaq listing rule 5250(c)(1)" in normalized
        and "matter is now closed" in normalized
    )
    if resolved:
        return {
            "phase": "resolved",
            "resolution_status": "closed",
            "lifecycle_topic": topic,
            "lifecycle_key": lifecycle_key,
            "resolution_signal": "now_complies_and_matter_closed",
        }
    if "not in compliance with nasdaq listing rule 5250(c)(1)" in normalized:
        return {
            "phase": "active",
            "resolution_status": "unknown",
            "lifecycle_topic": topic,
            "lifecycle_key": lifecycle_key,
            "resolution_signal": "explicit_noncompliance",
        }
    if (
        "nasdaq has granted" in normalized
        and "exception" in normalized
        and "listing rule 5250(c)(1)" in normalized
    ):
        return {
            "phase": "active",
            "resolution_status": "unknown",
            "lifecycle_topic": topic,
            "lifecycle_key": lifecycle_key,
            "resolution_signal": "temporary_exception_pending_filings",
        }
    return None


def apply_sec_listing_lifecycle(
    events: list[dict[str, Any]],
    classifications: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Link later verified resolution filings to earlier events of the same topic."""
    rows = [dict(item) for item in events]
    for row in rows:
        classified = classifications.get(str(row.get("source_record_id") or ""))
        if classified:
            row.update(classified)

    active_rows = [row for row in rows if row.get("phase") == "active"]
    resolutions = [row for row in rows if row.get("phase") == "resolved"]
    links: list[dict[str, Any]] = []
    resolving_ids: set[str] = set()
    for resolution in resolutions:
        resolved_date = _coerce_date(resolution.get("published_at"))
        if not resolved_date:
            continue
        resolution_id = str(resolution.get("source_record_id") or "")
        # A filing that explicitly says the matter is closed is never a fresh
        # negative event, even when the earlier notice fell outside this scan.
        resolving_ids.add(resolution_id)
        matched: list[dict[str, Any]] = []
        for event in active_rows:
            event_date = _coerce_date(event.get("published_at"))
            if (
                not event_date
                or event_date >= resolved_date
                or event.get("lifecycle_key") != resolution.get("lifecycle_key")
            ):
                continue
            matched.append(event)
        if not matched:
            continue
        matched_ids: list[str] = []
        for event in matched:
            event_id = str(
                event.get("canonical_event_id")
                or event.get("source_record_id")
                or event.get("url")
            )
            matched_ids.append(event_id)
            event["resolution_status"] = str(resolution.get("resolution_status") or "closed")
            event["resolved_at"] = resolved_date.isoformat()
            event["resolution_evidence"] = {
                "resolution_status": event["resolution_status"],
                "official_source": True,
                "entity_match": "exact",
                "entity_scope": "issuer",
                "url": str(resolution.get("url") or ""),
                "published_at": resolved_date.isoformat(),
                "source_record_id": resolution_id,
                "linked_event_id": event_id,
                "lifecycle_topic": event.get("lifecycle_topic"),
                "match_method": "SEC CIK+ticker+Item3.01+Nasdaq Rule 5250(c)(1)",
                "resolution_signal": resolution.get("resolution_signal"),
            }
        links.append(
            {
                "resolution_status": str(resolution.get("resolution_status") or "closed"),
                "official_source": True,
                "entity_match": "exact",
                "entity_scope": "issuer",
                "url": str(resolution.get("url") or ""),
                "title": str(resolution.get("title") or ""),
                "published_at": resolved_date.isoformat(),
                "source_record_id": resolution_id,
                "lifecycle_topic": resolution.get("lifecycle_topic"),
                "matched_event_ids": sorted(matched_ids),
                "match_method": "SEC CIK+ticker+Item3.01+Nasdaq Rule 5250(c)(1)",
                "resolution_signal": resolution.get("resolution_signal"),
            }
        )

    # A filing that explicitly closes the matter is lifecycle evidence, not a
    # fresh negative P1 event. Keep it in overlay.lifecycle.links only.
    kept = [
        row
        for row in rows
        if not (
            row.get("phase") == "resolved"
            and str(row.get("source_record_id") or "") in resolving_ids
        )
    ]
    return kept, links


def enrich_sec_listing_lifecycle(
    events: list[dict[str, Any]],
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    lookback_days: int = DEFAULT_EVENT_LOOKBACK_DAYS,
    as_of: dt.date | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, list[dict[str, str]]]:
    """Fetch official Item 3.01 filings and apply fail-closed lifecycle linking."""
    classifications: dict[str, dict[str, str]] = {}
    errors: list[dict[str, str]] = []
    scanned = 0
    as_of = as_of or dt.date.today()
    for event in events:
        if event.get("item_code") != "3.01" or not _is_official_event_url(str(event.get("url") or "")):
            continue
        event_date = _coerce_date(event.get("published_at"))
        if not event_date or not (0 <= (as_of - event_date).days <= lookback_days):
            continue
        source_record_id = str(event.get("source_record_id") or "")
        try:
            filing_text = _strip_html(
                _fetch_text(str(event["url"]), timeout_sec=timeout_sec)
            )
            scanned += 1
            classified = classify_sec_listing_lifecycle(filing_text)
            if classified:
                classifications[source_record_id] = classified
        except Exception as exc:  # noqa: BLE001 - unresolved is safer than a guessed resolution
            errors.append({"source_record_id": source_record_id, "error": str(exc)[:240]})
    linked_events, links = apply_sec_listing_lifecycle(events, classifications)
    return linked_events, links, scanned, errors


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
                {"source": "sec_trading_suspensions", "role": "official regulator trading suspension"},
                {"source": "sec_submissions", "role": "company filed events"},
            ]
        if market == "A":
            return [
                {"source": "cninfo", "role": "official company announcements and regulator decisions"},
                {"source": "csrc_penalties", "role": "central regulator penalty decisions"},
                {"source": "sse_discipline", "role": "SSE discipline and regulatory measures for .SH"},
                {"source": "szse_discipline", "role": "SZSE discipline and regulatory measures for .SZ"},
            ]
        if market == "HK":
            return [
                {"source": "hkex_discipline", "role": "HKEX issuer and related-person disciplinary actions"},
                {"source": "hkex_critical_filings", "role": "issuer-filed suspension and solvency events"},
                {"source": "sfc_enforcement", "role": "regulator enforcement"},
            ]
    return [{"source": "manual_official_source", "role": "official dated evidence required"}]


def _fetch_json(
    url: str,
    *,
    timeout_sec: int,
    headers: dict[str, str] | None = None,
) -> Any:
    return _fetch_json_request(url, timeout_sec=timeout_sec, headers=headers)


def _url_host(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")


def _is_sec_url(url: str) -> bool:
    host = _url_host(url)
    return host == "sec.gov" or host.endswith(".sec.gov")


def _declared_sec_user_agent() -> str:
    value = os.environ.get(SEC_USER_AGENT_ENV, "").strip()
    lowered = value.lower()
    email_match = _EMAIL_RE.search(value)
    email_domain = email_match.group(0).rsplit("@", 1)[-1].lower() if email_match else ""
    identity_text = _EMAIL_RE.sub(" ", value)
    if (
        not value
        or any(marker in lowered for marker in _SEC_PLACEHOLDER_MARKERS)
        or not email_match
        or email_domain in _SEC_PLACEHOLDER_EMAIL_DOMAINS
        or not re.search(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", identity_text)
    ):
        raise RuntimeError(
            f"SEC network access requires {SEC_USER_AGENT_ENV} with a truthful "
            "name or organization and a monitored contact email; placeholder "
            "or missing identities are rejected before any request."
        )
    return value


def _request_headers(
    url: str,
    *,
    accept: str,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    headers = {
        "User-Agent": DEFAULT_HTTP_USER_AGENT,
        "Accept": accept,
        **(overrides or {}),
    }
    if _is_sec_url(url):
        # Apply the declared contact after caller overrides so no call site can
        # accidentally replace it with a browser or placeholder identity.
        headers["User-Agent"] = _declared_sec_user_agent()
        headers["Accept-Encoding"] = "gzip, deflate"
    return headers


def _wait_for_sec_rate_limit(url: str) -> None:
    if not _is_sec_url(url):
        return
    global _SEC_LAST_REQUEST_AT
    with _SEC_RATE_LOCK:
        now = time.monotonic()
        remaining = SEC_REQUEST_INTERVAL_SEC - (now - _SEC_LAST_REQUEST_AT)
        if remaining > 0:
            time.sleep(remaining)
        _SEC_LAST_REQUEST_AT = time.monotonic()


def _urlopen(req: urllib.request.Request, *, timeout_sec: int):
    _wait_for_sec_rate_limit(req.full_url)
    try:
        return urllib.request.urlopen(req, timeout=timeout_sec)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            detail = f"; Retry-After={retry_after}" if retry_after else ""
            raise RuntimeError(
                f"HTTP 429 from {req.full_url}; SEC or source rate limit reached{detail}"
            ) from exc
        raise RuntimeError(f"HTTP {exc.code} from {req.full_url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error from {req.full_url}: {exc.reason}") from exc


def _read_response_bytes(resp: Any) -> bytes:
    raw = resp.read()
    content_encoding = (resp.headers.get("Content-Encoding") or "").lower()
    if "gzip" in content_encoding:
        return gzip.decompress(raw)
    if "deflate" in content_encoding:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def _fetch_json_request(
    url: str,
    *,
    timeout_sec: int,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    request_headers = _request_headers(
        url,
        accept="application/json",
        overrides=headers,
    )
    req = urllib.request.Request(url, data=data, headers=request_headers)
    with _urlopen(req, timeout_sec=timeout_sec) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return json.loads(_read_response_bytes(resp).decode(charset, errors="replace"))


def _post_json(url: str, payload: dict[str, Any], *, timeout_sec: int) -> dict[str, Any]:
    return _fetch_json_request(
        url,
        timeout_sec=timeout_sec,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def _fetch_text(url: str, *, timeout_sec: int, headers: dict[str, str] | None = None) -> str:
    request_headers = _request_headers(
        url,
        accept="text/html,application/xhtml+xml",
        overrides=headers,
    )
    req = urllib.request.Request(url, headers=request_headers)
    with _urlopen(req, timeout_sec=timeout_sec) as resp:
        raw = _read_response_bytes(resp)
        declared = resp.headers.get_content_charset()
        if declared:
            return raw.decode(declared, errors="replace")
        return raw.decode("utf-8", errors="replace")


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
        evidence["official_source"] = _is_official_event_url(evidence["url"])
        evidence["entity_match"] = "exact" if evidence["official_source"] else "unverified"
        evidence["entity_scope"] = "issuer"
        evidence["match_method"] = "cached_ticker_scope"
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


def _official_event_item(
    *,
    source: str,
    url: str,
    title: str,
    published_at: Any,
    severity: str,
    event_type: str,
    entity_scope: str,
    match_method: str,
    source_record_id: str,
) -> dict[str, Any]:
    item = _evidence_item(
        source=source,
        url=url,
        title=title,
        published_at=published_at,
        fields=["15_events.recent_news"],
    )
    item.update(
        {
            "severity": severity,
            "event_type": event_type,
            "official_source": _is_official_event_url(url),
            "entity_match": "exact",
            "entity_scope": entity_scope,
            "match_method": match_method,
            "source_record_id": source_record_id,
            "canonical_event_id": f"{source}:{source_record_id}",
            "resolution_status": "unknown",
        }
    )
    return item


def _add_adapter_events(overlay: dict[str, Any], source: str, events: list[dict[str, Any]]) -> None:
    overlay["field_mapping"][source] = {
        "events": [
            {
                "severity": item.get("severity"),
                "event_type": item.get("event_type"),
                "published_at": item.get("published_at"),
                "source_record_id": item.get("source_record_id"),
                "entity_scope": item.get("entity_scope"),
            }
            for item in events
        ]
    }
    overlay["evidence"].extend(events)


def _record_source_coverage(
    overlay: dict[str, Any],
    source: str,
    status: str,
    *,
    matched: int = 0,
    scanned: int = 0,
    failed: int = 0,
) -> None:
    overlay["source_coverage"].append(
        {
            "source": source,
            "status": status,
            "scanned": int(scanned),
            "matched": int(matched),
            "failed": int(failed),
        }
    )


def _record_source_error(overlay: dict[str, Any], source: str, error: Exception | str) -> None:
    message = str(error)[:300]
    overlay["errors"].append({"source": source, "error": message})
    _record_source_coverage(overlay, source, "error")


def _reconcile_source_coverage(overlay: dict[str, Any]) -> None:
    aliases = {
        "cninfo": {"cninfo_company_announcement"},
        "csrc_penalties": {"csrc_penalty_decision"},
        "sse_discipline": {"sse_discipline"},
        "szse_discipline": {"szse_discipline", "szse_regulatory_measure"},
        "hkex_discipline": {"hkex_disciplinary_action"},
        "hkex_critical_filings": {"hkex_issuer_critical_filing"},
        "sfc_enforcement": {"sfc_enforcement"},
        "sec_submissions": {"sec_submissions"},
        "sec_litigation_releases": {"sec_litigation_release"},
        "sec_trading_suspensions": {"sec_trading_suspension"},
    }
    evidence = overlay.get("evidence") or []
    for row in overlay.get("source_coverage") or []:
        sources = aliases.get(str(row.get("source")), {str(row.get("source"))})
        row["eligible"] = sum(1 for item in evidence if str(item.get("source")) in sources)


def _finalize_negative_events(
    evidence: list[dict[str, Any]],
    *,
    as_of: dt.date,
    lookback_days: int,
    max_items: int,
) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    severity_rank = {"P0": 0, "P1": 1, "P2": 2}
    for original in evidence:
        if not isinstance(original, dict):
            continue
        item = dict(original)
        published = _coerce_date(item.get("published_at"))
        if not published:
            continue
        age_days = (as_of - published).days
        if age_days < 0 or age_days > lookback_days:
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        severity = str(item.get("severity") or "")
        if not url or not title or severity not in severity_rank:
            continue
        item["url"] = url
        item["title"] = title
        item["published_at"] = published.isoformat()
        item["age_days"] = age_days
        item["as_of_date"] = as_of.isoformat()
        item["official_source"] = bool(item.get("official_source")) and _is_official_event_url(url)
        if item.get("entity_match") not in {"exact", "unverified"}:
            item["entity_match"] = "unverified"
        key = _canonical_event_key(item)
        previous = by_key.get(key)
        if previous is None or severity_rank[severity] < severity_rank[str(previous.get("severity"))]:
            by_key[key] = item
    rows = _merge_exchange_mirrors(list(by_key.values()), severity_rank=severity_rank)
    rows.sort(
        key=lambda item: (
            -severity_rank[str(item.get("severity"))],
            str(item.get("published_at") or ""),
            str(item.get("url") or ""),
        ),
        reverse=True,
    )
    return rows[:max_items]


def _merge_exchange_mirrors(
    rows: list[dict[str, Any]],
    *,
    severity_rank: dict[str, int],
) -> list[dict[str, Any]]:
    direct_by_authority = {
        "sse": [item for item in rows if item.get("source") == "sse_discipline"],
        "szse": [
            item
            for item in rows
            if item.get("source") in {"szse_discipline", "szse_regulatory_measure"}
        ],
    }
    kept: list[dict[str, Any]] = []
    for item in rows:
        if item.get("source") != "cninfo_company_announcement":
            kept.append(item)
            continue
        title = str(item.get("title") or "")
        authority = "szse" if "深圳证券交易所" in title else "sse" if "上海证券交易所" in title else None
        if not authority:
            kept.append(item)
            continue
        item_date = _coerce_date(item.get("published_at"))
        candidate = None
        for direct in direct_by_authority[authority]:
            direct_date = _coerce_date(direct.get("published_at"))
            if not item_date or not direct_date or abs((item_date - direct_date).days) > 10:
                continue
            if severity_rank[str(item.get("severity"))] < severity_rank[str(direct.get("severity"))]:
                continue
            candidate = direct
            break
        if candidate is None:
            kept.append(item)
            continue
        candidate.setdefault("corroborating_sources", []).append(str(item.get("source")))
        candidate.setdefault("corroborating_urls", []).append(str(item.get("url")))
    return kept


def _canonical_event_key(item: dict[str, Any]) -> str:
    parsed = urllib.parse.urlsplit(str(item.get("url") or ""))
    canonical_url = urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))
    if canonical_url:
        return canonical_url
    title = re.sub(r"\W+", "", str(item.get("title") or "").lower())
    return f"{item.get('published_at')}|{title}"


def _is_official_event_url(url: str) -> bool:
    try:
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in OFFICIAL_EVENT_HOST_SUFFIXES)


def _parse_iso_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid ISO date: {value}") from exc


def _coerce_date(value: Any) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, (int, float)):
        try:
            return dt.datetime.fromtimestamp(float(value) / 1000, tz=dt.timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return dt.date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def _timestamp_ms_to_date(value: Any) -> str | None:
    parsed = _coerce_date(value)
    return parsed.isoformat() if parsed else None


def _a_share_code(ticker: str) -> str:
    match = re.search(r"(^|[^0-9])(\d{6})(?:\.(?:SH|SZ|BJ))?$", ticker.upper())
    if not match:
        raise ValueError(f"invalid A-share ticker: {ticker}")
    return match.group(2)


def _hk_numeric_code(ticker: str) -> str:
    value = ticker.upper().removeprefix("HK_").removesuffix(".HK")
    if not value.isdigit():
        raise ValueError(f"invalid HK ticker: {ticker}")
    return str(int(value))


def _date_from_hkex_url(url: str) -> str | None:
    match = re.search(r"/(20\d{2})/(\d{2})(\d{2})(\d{2})news", url)
    if not match:
        return None
    year = int(match.group(1))
    if int(match.group(2)) != year % 100:
        return None
    try:
        return dt.date(year, int(match.group(3)), int(match.group(4))).isoformat()
    except ValueError:
        return None


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _strip_html(value: str) -> str:
    parser = _TextCollector()
    parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


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


def _attach_display_labels(overlay: dict[str, Any]) -> None:
    status = str(overlay.get("status") or "")
    target = str(overlay.get("target") or "")
    confidence = overlay.get("confidence") or {}
    level = str(confidence.get("level") or "")
    confidence["label_zh"] = CONFIDENCE_LABEL_ZH.get(level, level)
    confidence["factors_zh"] = [FACTOR_LABEL_ZH.get(str(item), str(item)) for item in confidence.get("factors") or []]
    overlay["confidence"] = confidence
    for item in overlay.get("evidence") or []:
        if isinstance(item, dict) and item.get("severity"):
            item["severity_label_zh"] = SEVERITY_LABEL_ZH.get(str(item["severity"]), str(item["severity"]))
    overlay["display"] = {
        "target_label_zh": TARGET_LABEL_ZH.get(target, target),
        "status_label_zh": STATUS_LABEL_ZH.get(status, status),
        "confidence_label_zh": confidence.get("label_zh", level),
        "summary_zh": _display_summary_zh(overlay),
    }


def _display_summary_zh(overlay: dict[str, Any]) -> str:
    ticker = overlay.get("ticker")
    target = TARGET_LABEL_ZH.get(str(overlay.get("target")), str(overlay.get("target")))
    status = STATUS_LABEL_ZH.get(str(overlay.get("status")), str(overlay.get("status")))
    confidence = (overlay.get("confidence") or {}).get("label_zh") or overlay.get("confidence", {}).get("level")
    return f"{ticker} {target}：{status}，置信度 {confidence}"


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
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_EVENT_LOOKBACK_DAYS)
    parser.add_argument("--source-record-limit", type=int, default=DEFAULT_SOURCE_RECORD_LIMIT)
    parser.add_argument("--as-of", help="Freeze recency relative to this YYYY-MM-DD date; defaults to today.")
    network_group = parser.add_mutually_exclusive_group()
    network_group.add_argument(
        "--allow-network",
        action="store_true",
        help="Explicitly allow official-source network requests; default is offline.",
    )
    network_group.add_argument(
        "--no-network",
        action="store_true",
        help="Deprecated compatibility flag; network is already disabled by default.",
    )
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    overlay = build_overlay(
        args.ticker,
        args.target,
        network=args.allow_network and not args.no_network,
        timeout_sec=args.timeout,
        max_items=args.max_items,
        lookback_days=args.lookback_days,
        source_record_limit=args.source_record_limit,
        as_of=args.as_of,
    )
    if not args.no_write:
        path = write_overlay(overlay, Path(args.output_dir))
        print(f"wrote {path}")
    print(
        json.dumps(
            {
                "ticker": overlay["ticker"],
                "target": overlay["target"],
                "target_label_zh": (overlay.get("display") or {}).get("target_label_zh"),
                "status": overlay["status"],
                "status_label_zh": (overlay.get("display") or {}).get("status_label_zh"),
                "confidence": overlay["confidence"],
                "elapsed_sec": overlay["performance"]["elapsed_sec"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if overlay["status"] in {"ready", "partial", "gap"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
