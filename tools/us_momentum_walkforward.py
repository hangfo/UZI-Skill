#!/usr/bin/env python3
"""Leak-free walk-forward validation for UZI's existing US technical score.

This is a research-only validator.  It reconstructs only the point-in-time
technical dimension from real Yahoo adjusted daily prices.  It does not pretend
that current news, fundamentals, or the full UZI score were historically known.
Signals are observed at day t, entered at the next close, and sampled with a
stride equal to the forward horizon so observations do not overlap within an
issuer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_kline import compute_indicators  # noqa: E402


DEFAULT_TICKERS = [
    "AAPL", "AMD", "HOOD", "BMNR", "MU", "SNDK", "KNSA", "OSCR",
    "IQV", "ITRI", "LCID", "NVDA", "MSTR", "NU", "MARA", "T",
    "SOFI", "JBLU", "INTC", "NOK", "FOUR", "CLS", "RGEN", "WDC",
    "STX", "GEV", "CRCL", "AI", "GEN", "ON", "IT", "CAT", "META",
    "GOOGL", "F", "PLTR", "COIN",
]
DEFAULT_HORIZONS = [21, 63, 126]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UZI-WalkForward/1.0"


def _universe_audit(
    manifest: dict[str, Any] | None,
    requested_tickers: list[str],
    fetch_failures: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, list[tuple[str, str | None]]]]:
    """Validate whether a universe can support parameter-tuning claims.

    A current or hand-picked ticker list can still be useful as a stress test,
    but it is never evidence for optimizing momentum weights.  Eligibility
    requires a complete point-in-time archive, explicit delisted coverage and
    successful price retrieval for every requested member.
    """
    requested = {str(t).upper() for t in requested_tickers}
    failures = fetch_failures or {}
    membership: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    reasons: list[str] = []
    if not manifest:
        return ({
            "status": "selected_universe_only",
            "parameter_tuning_allowed": False,
            "point_in_time": False,
            "includes_delisted": False,
            "complete_universe": False,
            "reasons": [
                "no point-in-time universe manifest",
                "current/popular tickers create selection and survivorship bias",
            ],
        }, {})

    if manifest.get("schema") != "uzi.us_point_in_time_universe.v1":
        reasons.append("unsupported universe manifest schema")
    if manifest.get("source_type") not in {"official_listing_archive", "licensed_point_in_time_database"}:
        reasons.append("source is not an official archive or licensed point-in-time database")
    if manifest.get("lookahead_free") is not True:
        reasons.append("lookahead_free is not explicitly true")
    if manifest.get("includes_delisted") is not True:
        reasons.append("delisted securities are not included")
    if manifest.get("complete_universe") is not True:
        reasons.append("universe completeness is not attested")
    if not manifest.get("source") or not manifest.get("source_url"):
        reasons.append("source provenance is incomplete")

    members = manifest.get("memberships") or []
    if not isinstance(members, list) or not members:
        reasons.append("membership history is empty")
        members = []
    delisted_members = 0
    for row in members:
        ticker = str((row or {}).get("ticker") or "").upper()
        start = str((row or {}).get("effective_from") or "")
        end_value = (row or {}).get("effective_to")
        end = str(end_value) if end_value else None
        try:
            if not ticker or not start:
                raise ValueError
            datetime.fromisoformat(start)
            if end:
                datetime.fromisoformat(end)
                if end < start:
                    raise ValueError
                delisted_members += 1
        except (TypeError, ValueError):
            reasons.append(f"invalid membership interval for {ticker or '<missing>'}")
            continue
        membership[ticker].append((start, end))

    missing = sorted(requested - set(membership))
    extra = sorted(set(membership) - requested)
    if missing:
        reasons.append("requested tickers missing from membership history: " + ",".join(missing))
    if extra:
        reasons.append("manifest universe was only partially requested: " + ",".join(extra[:10]))
    if delisted_members == 0:
        reasons.append("no finite membership interval demonstrates delisted coverage")
    failed_members = sorted(t for t in failures if t in requested)
    if failed_members:
        reasons.append("price retrieval failed for universe members: " + ",".join(failed_members))

    allowed = not reasons
    return ({
        "status": "optimization_eligible" if allowed else "universe_contract_failed",
        "parameter_tuning_allowed": allowed,
        "point_in_time": True,
        "includes_delisted": manifest.get("includes_delisted") is True,
        "complete_universe": manifest.get("complete_universe") is True,
        "source": manifest.get("source"),
        "source_url": manifest.get("source_url"),
        "members": len(membership),
        "finite_memberships": delisted_members,
        "reasons": reasons,
    }, dict(membership))


def _membership_allows(
    membership: dict[str, list[tuple[str, str | None]]], ticker: str, signal_date: str
) -> bool:
    if not membership:
        return True
    return any(start <= signal_date and (end is None or signal_date <= end)
               for start, end in membership.get(ticker, []))


def _fetch_yahoo_daily(ticker: str, range_: str, retries: int = 3) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({
        "interval": "1d",
        "range": range_,
        "events": "div,splits",
        "includeAdjustedClose": "true",
    })
    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(ticker)}?{query}"
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            result = (payload.get("chart", {}).get("result") or [None])[0]
            if not result:
                raise RuntimeError(payload.get("chart", {}).get("error") or "empty chart")
            timestamps = result.get("timestamp") or []
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            adjusted = (result.get("indicators", {}).get("adjclose") or [{}])[0].get(
                "adjclose"
            ) or []
            raw_closes = quote.get("close") or []
            rows: list[dict[str, Any]] = []
            for index, timestamp in enumerate(timestamps):
                raw_close = raw_closes[index] if index < len(raw_closes) else None
                adj_close = adjusted[index] if index < len(adjusted) else raw_close
                if raw_close is None or adj_close is None or float(adj_close) <= 0:
                    continue
                scale = float(adj_close) / float(raw_close) if float(raw_close) else 1.0

                def value(key: str, default: float) -> float:
                    values = quote.get(key) or []
                    item = values[index] if index < len(values) else None
                    return (float(item) if item is not None else default) * scale

                volumes = quote.get("volume") or []
                volume = volumes[index] if index < len(volumes) else None
                rows.append({
                    "Date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
                    "Open": value("open", float(adj_close)),
                    "High": value("high", float(adj_close)),
                    "Low": value("low", float(adj_close)),
                    "Close": float(adj_close),
                    "Volume": float(volume) if volume is not None else 0.0,
                })
            if not rows:
                raise RuntimeError("no valid adjusted daily rows")
            return rows
        except Exception as exc:  # network errors are retried, then surfaced
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{ticker}: {last_error}")


def _max_drawdown(closes: list[float], window: int = 252) -> float:
    values = closes[-window:]
    peak = values[0]
    worst = 0.0
    for close in values:
        peak = max(peak, close)
        worst = min(worst, close / peak - 1.0)
    return worst * 100.0


def _technical_score(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    """Reproduce score_dimensions() dimension-2 logic without other dimensions."""
    indicators = compute_indicators(rows)
    stage = int(indicators.get("stage") or 0)
    score = 5
    if stage == 2:
        score += 2
    elif stage == 1:
        score += 1
    elif stage in (3, 4):
        score -= 2
    if indicators.get("ma_bull_alignment") is True:
        score += 1
    drawdown = _max_drawdown([float(row["Close"]) for row in rows])
    if drawdown <= -30:
        score -= 1
    return max(1, min(10, score)), {
        "stage": stage,
        "ma_bull_alignment": indicators.get("ma_bull_alignment"),
        "max_drawdown_1y_pct": round(drawdown, 4),
    }


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + end - 1) / 2.0 + 1.0
        for pos in order[start:end]:
            ranks[pos] = rank
        start = end
    return ranks


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    lm, rm = statistics.mean(left), statistics.mean(right)
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    ld = math.sqrt(sum((a - lm) ** 2 for a in left))
    rd = math.sqrt(sum((b - rm) ** 2 for b in right))
    return numerator / (ld * rd) if ld and rd else None


def _spearman(rows: list[dict[str, Any]], field: str) -> float | None:
    scores = [float(row["technical_score"]) for row in rows]
    returns = [float(row[field]) for row in rows]
    return _pearson(_rank(scores), _rank(returns))


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    net = [float(row["net_return_pct"]) for row in rows]
    excess = [float(row["excess_vs_spy_pct"]) for row in rows]
    issuer_net: dict[str, list[float]] = defaultdict(list)
    issuer_excess: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        issuer_net[row["ticker"]].append(float(row["net_return_pct"]))
        issuer_excess[row["ticker"]].append(float(row["excess_vs_spy_pct"]))
    return {
        "n": len(rows),
        "issuers": len({row["ticker"] for row in rows}),
        "mean_net_return_pct": round(statistics.mean(net), 4) if net else None,
        "median_net_return_pct": round(statistics.median(net), 4) if net else None,
        "positive_rate_pct": round(sum(value > 0 for value in net) / len(net) * 100, 2)
        if net else None,
        "mean_excess_vs_spy_pct": round(statistics.mean(excess), 4) if excess else None,
        "median_excess_vs_spy_pct": round(statistics.median(excess), 4) if excess else None,
        "issuer_equal_mean_net_return_pct": round(statistics.mean(
            statistics.mean(values) for values in issuer_net.values()
        ), 4) if issuer_net else None,
        "issuer_equal_mean_excess_vs_spy_pct": round(statistics.mean(
            statistics.mean(values) for values in issuer_excess.values()
        ), 4) if issuer_excess else None,
        "beat_spy_rate_pct": round(sum(value > 0 for value in excess) / len(excess) * 100, 2)
        if excess else None,
        "p10_net_return_pct": round(_percentile(net, 0.10), 4) if net else None,
        "worst_net_return_pct": round(min(net), 4) if net else None,
    }


def _build_signals(
    bars: dict[str, list[dict[str, Any]]],
    benchmark: list[dict[str, Any]],
    horizons: Iterable[int],
    min_history: int,
    round_trip_cost_bps: float,
    membership: dict[str, list[tuple[str, str | None]]] | None = None,
) -> list[dict[str, Any]]:
    spy_by_date = {row["Date"]: float(row["Close"]) for row in benchmark}
    signals: list[dict[str, Any]] = []
    for ticker, rows in bars.items():
        score_cache: dict[int, tuple[int, dict[str, Any]]] = {}
        for horizon in horizons:
            last_signal = len(rows) - horizon - 2
            for index in range(min_history - 1, last_signal + 1, horizon):
                if not _membership_allows(membership or {}, ticker, rows[index]["Date"]):
                    continue
                entry = rows[index + 1]
                exit_ = rows[index + 1 + horizon]
                spy_entry = spy_by_date.get(entry["Date"])
                spy_exit = spy_by_date.get(exit_["Date"])
                if not spy_entry or not spy_exit:
                    continue
                if index not in score_cache:
                    # Every production input consumed by dimension 2 is bounded
                    # by 260 rows (MA200 slope needs 200 + 60 observations; the
                    # drawdown window needs 252).  Keeping older history would
                    # only rescan irrelevant rows and cannot change the score.
                    score_cache[index] = _technical_score(
                        rows[max(0, index + 1 - 260): index + 1]
                    )
                score, context = score_cache[index]
                gross = (float(exit_["Close"]) / float(entry["Close"]) - 1.0) * 100.0
                spy_return = (spy_exit / spy_entry - 1.0) * 100.0
                signals.append({
                    "ticker": ticker,
                    "horizon_days": horizon,
                    "signal_date": rows[index]["Date"],
                    "entry_date": entry["Date"],
                    "exit_date": exit_["Date"],
                    "technical_score": score,
                    **context,
                    "gross_return_pct": round(gross, 4),
                    "net_return_pct": round(gross - round_trip_cost_bps / 100.0, 4),
                    "spy_return_pct": round(spy_return, 4),
                    "excess_vs_spy_pct": round(gross - spy_return, 4),
                })
    return signals


def _analyze(signals: list[dict[str, Any]], horizons: Iterable[int]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for horizon in horizons:
        rows = [row for row in signals if row["horizon_days"] == horizon]
        by_score = {
            str(score): _summary([row for row in rows if row["technical_score"] == score])
            for score in sorted({row["technical_score"] for row in rows})
        }
        top = [row for row in rows if row["technical_score"] >= 7]
        low = [row for row in rows if row["technical_score"] <= 4]
        stage_2 = [row for row in rows if row["stage"] == 2]
        stage_4 = [row for row in rows if row["stage"] == 4]
        top_summary, low_summary = _summary(top), _summary(low)
        stage_2_summary, stage_4_summary = _summary(stage_2), _summary(stage_4)

        def spread(left: dict[str, Any], right: dict[str, Any], key: str) -> float | None:
            if left.get(key) is None or right.get(key) is None:
                return None
            return round(float(left[key]) - float(right[key]), 4)

        result[str(horizon)] = {
            "all": _summary(rows),
            "by_score": by_score,
            "score_spearman_net_return": (
                round(value, 6) if (value := _spearman(rows, "net_return_pct")) is not None else None
            ),
            "score_spearman_excess_vs_spy": (
                round(value, 6)
                if (value := _spearman(rows, "excess_vs_spy_pct")) is not None else None
            ),
            "top_score_7_plus": top_summary,
            "low_score_4_minus": low_summary,
            "top_minus_low_mean_net_pct": spread(
                top_summary, low_summary, "mean_net_return_pct"
            ),
            "top_minus_low_mean_excess_pct": spread(
                top_summary, low_summary, "mean_excess_vs_spy_pct"
            ),
            "top_minus_low_median_net_pct": spread(
                top_summary, low_summary, "median_net_return_pct"
            ),
            "top_minus_low_median_excess_pct": spread(
                top_summary, low_summary, "median_excess_vs_spy_pct"
            ),
            "stage_2": stage_2_summary,
            "stage_4": stage_4_summary,
            "stage_2_minus_4_mean_net_pct": spread(
                stage_2_summary, stage_4_summary, "mean_net_return_pct"
            ),
            "stage_2_minus_4_mean_excess_pct": spread(
                stage_2_summary, stage_4_summary, "mean_excess_vs_spy_pct"
            ),
            "stage_2_minus_4_median_net_pct": spread(
                stage_2_summary, stage_4_summary, "median_net_return_pct"
            ),
            "stage_2_minus_4_median_excess_pct": spread(
                stage_2_summary, stage_4_summary, "median_excess_vs_spy_pct"
            ),
        }
    return result


def _markdown(result: dict[str, Any]) -> str:
    lines = [
        "# US momentum technical-score walk-forward",
        "",
        f"- captured_at_utc: `{result['captured_at_utc']}`",
        f"- source: `{result['source']}`",
        f"- universe: `{', '.join(result['tickers'])}`",
        f"- benchmark: `{result['benchmark']}`",
        f"- universe audit: `{result['universe_audit']['status']}`; parameter tuning allowed: `{result['universe_audit']['parameter_tuning_allowed']}`",
        f"- input_sha256: `{result['input_sha256']}`",
        f"- signals: `{len(result['signals'])}`; failures: `{len(result['fetch_failures'])}`",
        "",
        "| horizon | n | score rho net | score rho excess | top-low net | top-low excess | Stage2-4 net | Stage2-4 excess |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for horizon, row in result["analysis"].items():
        lines.append(
            f"| {horizon} | {row['all']['n']} | {row['score_spearman_net_return']} | "
            f"{row['score_spearman_excess_vs_spy']} | {row['top_minus_low_mean_net_pct']} | "
            f"{row['top_minus_low_mean_excess_pct']} | "
            f"{row['stage_2_minus_4_mean_net_pct']} | "
            f"{row['stage_2_minus_4_mean_excess_pct']} |"
        )
    lines.extend([
        "",
        "Signals use data available through the signal close, enter at the next close, "
        "and use a horizon-sized stride per issuer. Returns use Yahoo adjusted close. "
        "Net return subtracts the configured round-trip cost; excess return is gross "
        "issuer return minus SPY over the identical dates.",
        "",
        "This validates only the historically reconstructable technical dimension. "
        "It is not a backtest of current news, entity matching, fundamentals, or the "
        "full UZI composite score.",
        "",
        "Unless universe_audit is optimization_eligible, these results are stress-test "
        "evidence only and must not change production parameters.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--range", default="10y")
    parser.add_argument("--horizons", nargs="+", type=int, default=DEFAULT_HORIZONS)
    parser.add_argument("--min-history", type=int, default=260)
    parser.add_argument("--round-trip-cost-bps", type=float, default=20.0)
    parser.add_argument("--prices-in", type=Path)
    parser.add_argument("--universe-manifest", type=Path)
    parser.add_argument("--prices-out", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    tickers = list(dict.fromkeys(ticker.upper() for ticker in args.tickers))
    if args.prices_in:
        frozen_prices = json.loads(args.prices_in.read_text(encoding="utf-8"))
        bars = frozen_prices["bars"]
        benchmark_rows = frozen_prices["benchmark"][args.benchmark.upper()]
        failures = frozen_prices.get("fetch_failures") or {}
    else:
        failures: dict[str, str] = {}
        bars: dict[str, list[dict[str, Any]]] = {}
        for ticker in [args.benchmark.upper(), *tickers]:
            try:
                rows = _fetch_yahoo_daily(ticker, args.range)
                if ticker == args.benchmark.upper():
                    benchmark_rows = rows
                else:
                    bars[ticker] = rows
            except Exception as exc:
                failures[ticker] = str(exc)
        if args.benchmark.upper() in failures:
            raise RuntimeError(f"benchmark fetch failed: {failures[args.benchmark.upper()]}")
        frozen_prices = {
            "schema": "uzi.us_adjusted_daily_prices.v1",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "Yahoo Finance chart v8 adjusted daily prices",
            "range": args.range,
            "benchmark": {args.benchmark.upper(): benchmark_rows},
            "bars": bars,
            "fetch_failures": failures,
        }
    price_payload = {
        "benchmark": frozen_prices["benchmark"],
        "bars": frozen_prices["bars"],
    }
    serialized = json.dumps(
        price_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    input_hash = hashlib.sha256(serialized).hexdigest()
    if args.prices_out:
        args.prices_out.parent.mkdir(parents=True, exist_ok=True)
        args.prices_out.write_bytes(
            json.dumps(frozen_prices, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )

    manifest = (json.loads(args.universe_manifest.read_text(encoding="utf-8"))
                if args.universe_manifest else None)
    universe_audit, membership = _universe_audit(manifest, tickers, failures)
    signals = _build_signals(
        bars,
        benchmark_rows,
        args.horizons,
        args.min_history,
        args.round_trip_cost_bps,
        membership=membership,
    )
    result = {
        "schema": "uzi.us_momentum_walkforward.v1",
        "captured_at_utc": frozen_prices["captured_at_utc"],
        "source": frozen_prices["source"],
        "input_sha256": input_hash,
        "tickers": list(bars),
        "benchmark": args.benchmark.upper(),
        "range": args.range,
        "horizons": args.horizons,
        "min_history": args.min_history,
        "round_trip_cost_bps": args.round_trip_cost_bps,
        "sampling": "signal at close t; entry next close; non-overlap stride=horizon per issuer",
        "universe_audit": universe_audit,
        "fetch_failures": failures,
        "analysis": _analyze(signals, args.horizons),
        "temporal_holdouts": {
            "through_2022": _analyze(
                [row for row in signals if row["signal_date"] < "2023-01-01"],
                args.horizons,
            ),
            "2023_onward": _analyze(
                [row for row in signals if row["signal_date"] >= "2023-01-01"],
                args.horizons,
            ),
        },
        "signals": signals,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({
        "captured_at_utc": result["captured_at_utc"],
        "input_sha256": input_hash,
        "tickers": len(bars),
        "failures": failures,
        "signals": len(signals),
        "analysis": result["analysis"],
        "universe_audit": universe_audit,
    }, ensure_ascii=False))
    return 0 if bars and signals else 1


if __name__ == "__main__":
    raise SystemExit(main())
