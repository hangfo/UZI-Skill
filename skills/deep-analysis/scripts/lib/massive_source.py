"""Massive Stocks Basic end-of-day shadow validator.

Massive is never treated as a real-time source on the free plan.  It may
corroborate completed daily bars and expose stale-tail conflicts, but it never
overwrites the primary Yahoo/yfinance series.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from zoneinfo import ZoneInfo

from lib.cache import TTL_DAILY, cached


MASSIVE_BASE_URL = "https://api.massive.com"
_NEW_YORK = ZoneInfo("America/New_York")


def _redacted_error(exc: Exception) -> RuntimeError:
    key = os.environ.get("MASSIVE_API_KEY", "")
    text = str(exc).replace(key, "[REDACTED]") if key else str(exc)
    return RuntimeError(f"Massive request failed: {text[:180]}")


def _bar_date(timestamp_ms: Any) -> str | None:
    try:
        moment = dt.datetime.fromtimestamp(
            float(timestamp_ms) / 1000.0,
            tz=dt.timezone.utc,
        ).astimezone(_NEW_YORK)
        return moment.date().isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def fetch_massive_eod(
    ticker: str,
    *,
    lookback_days: int = 14,
    network: bool = True,
    timeout_sec: int = 12,
) -> list[dict[str, Any]]:
    """Fetch split-adjusted completed daily aggregates using Bearer auth."""
    if not network:
        return []
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("MASSIVE_API_KEY is not configured")
    symbol = str(ticker or "").strip().upper()
    if not symbol or not all(ch.isalnum() or ch in ".-" for ch in symbol):
        raise ValueError("invalid Massive stock ticker")
    end = dt.date.today()
    start = end - dt.timedelta(days=max(5, min(int(lookback_days), 60)))
    path = (
        f"/v2/aggs/ticker/{urllib.parse.quote(symbol, safe='.-')}"
        f"/range/1/day/{start.isoformat()}/{end.isoformat()}"
    )
    query = urllib.parse.urlencode(
        {"adjusted": "true", "sort": "asc", "limit": 120}
    )
    request = urllib.request.Request(
        f"{MASSIVE_BASE_URL}{path}?{query}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "UZI-Skill EOD shadow/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise _redacted_error(exc) from exc
    rows = []
    for item in payload.get("results") or []:
        date = _bar_date(item.get("t"))
        if not date:
            continue
        rows.append(
            {
                "date": date,
                "open": item.get("o"),
                "high": item.get("h"),
                "low": item.get("l"),
                "close": item.get("c"),
                "volume": item.get("v"),
                "transactions": item.get("n"),
                "vwap": item.get("vw"),
            }
        )
    rows.sort(key=lambda row: row["date"])
    return rows


def _primary_row_date(row: dict[str, Any]) -> str | None:
    value = row.get("日期")
    if value is None:
        value = row.get("Date")
    if value is None:
        value = row.get("date")
    if value is None:
        return None
    if hasattr(value, "date"):
        try:
            return value.date().isoformat()
        except (AttributeError, TypeError, ValueError):
            pass
    text = str(value).strip()
    return text[:10] if len(text) >= 10 and text[4:5] == "-" else None


def _primary_close(row: dict[str, Any]) -> float | None:
    for key in ("收盘", "Close", "close"):
        value = row.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def compare_massive_eod(
    ticker: str,
    primary_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a non-mutating freshness/close comparison for the latest bar."""
    if not os.environ.get("MASSIVE_API_KEY"):
        return {
            "status": "gap",
            "reason": "MASSIVE_API_KEY not configured",
            "plan_semantics": "Stocks Basic is end-of-day, not real-time",
        }
    valid_primary = [
        (date, row)
        for row in primary_rows
        if (date := _primary_row_date(row))
    ]
    if not valid_primary:
        return {"status": "gap", "reason": "primary daily series has no dated rows"}
    try:
        massive_rows = cached(
            ticker.upper(),
            "massive_eod_shadow_v1",
            lambda: fetch_massive_eod(ticker),
            ttl=TTL_DAILY,
        )
    except Exception as exc:
        return {
            "status": "gap",
            "reason": type(exc).__name__,
            "plan_semantics": "Stocks Basic is end-of-day, not real-time",
        }
    if not massive_rows:
        return {"status": "gap", "reason": "Massive returned no completed EOD bars"}
    primary_date, primary_row = max(valid_primary, key=lambda pair: pair[0])
    massive_row = massive_rows[-1]
    massive_date = massive_row["date"]
    primary_close = _primary_close(primary_row)
    massive_close = massive_row.get("close")
    close_diff_pct = None
    if (
        primary_date == massive_date
        and primary_close not in (None, 0)
        and massive_close is not None
    ):
        close_diff_pct = (float(massive_close) / primary_close - 1.0) * 100.0
    try:
        session_gap_days = (
            dt.date.fromisoformat(primary_date)
            - dt.date.fromisoformat(massive_date)
        ).days
    except (TypeError, ValueError):
        session_gap_days = None
    if massive_date > primary_date:
        status = "primary_stale"
    elif massive_date < primary_date:
        status = "massive_delayed_or_market_open"
    elif close_diff_pct is None:
        status = "same_date_uncomparable"
    elif abs(close_diff_pct) <= 0.05:
        status = "match"
    else:
        status = "same_date_close_conflict"
    return {
        "status": status,
        "primary": {"date": primary_date, "close": primary_close},
        "massive": {"date": massive_date, "close": massive_close},
        "calendar_gap_days": session_gap_days,
        "close_diff_pct": round(close_diff_pct, 6) if close_diff_pct is not None else None,
        "plan_semantics": "Stocks Basic is end-of-day, not real-time",
        "adjustment_note": (
            "Massive aggregates are split-adjusted but not dividend-adjusted; "
            "never splice them into total-return backtests."
        ),
        "overwrote_primary": False,
    }
