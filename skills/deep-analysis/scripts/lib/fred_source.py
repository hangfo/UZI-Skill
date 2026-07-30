"""Official FRED macro observations used as evidence-only US context.

This module deliberately does not translate observations into bullish/bearish
labels.  It preserves values, observation dates, and real-time/vintage dates so
the scoring layer cannot silently treat missing or revised data as neutral.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from lib.cache import cached


FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = {
    "DFF": {"label": "Effective Federal Funds Rate", "frequency": "daily"},
    "DGS2": {"label": "2-Year Treasury Rate", "frequency": "daily"},
    "DGS10": {"label": "10-Year Treasury Rate", "frequency": "daily"},
    "T10Y2Y": {"label": "10Y minus 2Y Treasury Spread", "frequency": "daily"},
    "BAMLH0A0HYM2": {"label": "US High Yield Option-Adjusted Spread", "frequency": "daily"},
    "VIXCLS": {"label": "CBOE VIX Close", "frequency": "daily"},
    "CPIAUCSL": {"label": "Consumer Price Index", "frequency": "monthly"},
    "UNRATE": {"label": "Unemployment Rate", "frequency": "monthly"},
}
FRED_CACHE_TTL_SEC = 6 * 60 * 60


def _redacted_error(exc: Exception) -> RuntimeError:
    key = os.environ.get("FRED_API_KEY", "")
    text = str(exc).replace(key, "[REDACTED]") if key else str(exc)
    return RuntimeError(f"FRED request failed: {text[:180]}")


def fetch_fred_series(
    series_id: str,
    *,
    limit: int = 3,
    as_of: str | None = None,
    network: bool = True,
    timeout_sec: int = 12,
) -> list[dict[str, Any]]:
    """Return latest non-missing observations in descending date order."""
    if not network:
        return []
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        raise RuntimeError("FRED_API_KEY is not configured")
    symbol = str(series_id or "").strip().upper()
    if symbol not in FRED_SERIES:
        raise ValueError(f"unsupported FRED series: {symbol}")
    params = {
        "series_id": symbol,
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": max(1, min(int(limit), 100)),
    }
    if as_of:
        params["realtime_start"] = as_of
        params["realtime_end"] = as_of
        params["observation_end"] = as_of
    url = FRED_BASE_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "UZI-Skill macro evidence/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise _redacted_error(exc) from exc
    rows = []
    for item in payload.get("observations") or []:
        value = item.get("value")
        if value in (None, "", "."):
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "series_id": symbol,
                "date": item.get("date"),
                "value": numeric,
                "realtime_start": item.get("realtime_start"),
                "realtime_end": item.get("realtime_end"),
            }
        )
    return rows


def fetch_fred_macro_snapshot(*, as_of: str | None = None) -> dict[str, Any]:
    """Fetch and cache a bounded official snapshot without interpreting it."""
    if not os.environ.get("FRED_API_KEY"):
        return {
            "status": "gap",
            "reason": "FRED_API_KEY not configured",
            "observations": {},
        }
    effective_as_of = as_of or dt.date.today().isoformat()
    cache_key = f"fred_macro_snapshot_v1_{effective_as_of}"

    def _fetch() -> dict[str, Any]:
        observations: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for series_id, metadata in FRED_SERIES.items():
            try:
                rows = fetch_fred_series(
                    series_id,
                    limit=3,
                    as_of=as_of,
                )
                if rows:
                    observations[series_id] = {
                        **metadata,
                        "latest": rows[0],
                        "recent": rows,
                    }
                else:
                    errors[series_id] = "no non-missing observations"
            except Exception as exc:
                errors[series_id] = type(exc).__name__
        return {
            "status": "ready" if observations else "gap",
            "as_of": effective_as_of,
            "captured_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "observations": observations,
            "errors": errors,
            "interpretation": None,
            "note": (
                "Official observations only; no bullish/bearish inference. "
                "Historical research must preserve ALFRED/FRED real-time vintages."
            ),
        }

    return cached(
        "_global",
        cache_key,
        _fetch,
        ttl=FRED_CACHE_TTL_SEC,
    )
