#!/usr/bin/env python3
"""Leak-free A-share walk-forward for UZI's existing technical dimension.

This research-only validator mirrors ``us_momentum_walkforward.py`` while
loading real qfq A-share daily bars through UZI's existing source chain.  It
does not change production scoring and does not reconstruct news,
fundamentals, or the full composite score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib.data_sources import fetch_kline  # noqa: E402
from lib.market_router import parse_ticker  # noqa: E402
from lib.providers.baostock_provider import _BaostockProvider  # noqa: E402
from us_momentum_walkforward import _analyze, _build_signals  # noqa: E402


def _normalise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aliases = {
        "Date": ("Date", "date", "日期"),
        "Open": ("Open", "open", "开盘"),
        "High": ("High", "high", "最高"),
        "Low": ("Low", "low", "最低"),
        "Close": ("Close", "close", "收盘"),
        "Volume": ("Volume", "volume", "成交量"),
    }

    def pick(row: dict[str, Any], names: tuple[str, ...], default: Any = None) -> Any:
        for name in names:
            if row.get(name) not in (None, ""):
                return row[name]
        return default

    by_date: dict[str, dict[str, Any]] = {}
    for row in rows:
        date = str(pick(row, aliases["Date"], ""))[:10]
        close = float(pick(row, aliases["Close"], 0) or 0)
        if len(date) != 10 or close <= 0:
            continue
        by_date[date] = {
            "Date": date,
            "Open": float(pick(row, aliases["Open"], close) or close),
            "High": float(pick(row, aliases["High"], close) or close),
            "Low": float(pick(row, aliases["Low"], close) or close),
            "Close": close,
            "Volume": float(pick(row, aliases["Volume"], 0) or 0),
        }
    return [by_date[date] for date in sorted(by_date)]


def _fetch_history(ticker: str, start: str, required_rows: int) -> tuple[list[dict[str, Any]], str]:
    """Reject a shallow primary history and fall back to BaoStock."""
    primary = _normalise(fetch_kline(parse_ticker(ticker), start=start, adjust="qfq"))
    if len(primary) >= required_rows:
        return primary, "UZI A-share source chain"

    start_iso = f"{start[:4]}-{start[4:6]}-{start[6:8]}"
    fallback = _normalise(_BaostockProvider().fetch_kline_a(ticker, start=start_iso))
    if len(fallback) > len(primary):
        return fallback, "BaoStock qfq fallback after shallow primary history"
    return primary, "UZI A-share source chain (history shorter than requested)"


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# A-share momentum technical-score walk-forward",
        "",
        f"- captured_at_utc: `{result['captured_at_utc']}`",
        f"- source: `{result['source']}`",
        f"- universe: `{', '.join(result['tickers'])}`",
        f"- benchmark: `{result['benchmark']}`",
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
        "Signals use data available through close t, enter at the next close, and use a horizon-sized stride.",
        "Prices are qfq-adjusted daily bars; excess return uses the broad-market benchmark over identical dates.",
        "This validates only the historically reconstructable technical dimension, not the full UZI score.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", required=True)
    parser.add_argument("--benchmark", default="000300.SH")
    parser.add_argument("--start", default="20160824")
    parser.add_argument("--horizons", nargs="+", type=int, default=[21, 63, 126])
    parser.add_argument("--min-history", type=int, default=260)
    parser.add_argument("--round-trip-cost-bps", type=float, default=30.0)
    parser.add_argument("--prices-out", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    tickers = list(dict.fromkeys(value.upper() for value in args.tickers))
    failures: dict[str, str] = {}
    bars: dict[str, list[dict[str, Any]]] = {}
    source_by_symbol: dict[str, str] = {}
    required_rows = args.min_history + max(args.horizons) + 1

    try:
        benchmark_rows, source_by_symbol[args.benchmark.upper()] = _fetch_history(
            args.benchmark, args.start, required_rows
        )
        if len(benchmark_rows) < required_rows:
            raise RuntimeError(
                f"only {len(benchmark_rows)} valid benchmark bars; need {required_rows}"
            )
    except Exception as exc:
        raise RuntimeError(f"benchmark fetch failed: {exc}") from exc

    for ticker in tickers:
        try:
            rows, source_by_symbol[ticker] = _fetch_history(ticker, args.start, required_rows)
            if len(rows) < required_rows:
                raise RuntimeError(f"only {len(rows)} valid daily bars; need {required_rows}")
            bars[ticker] = rows
        except Exception as exc:
            failures[ticker] = f"{type(exc).__name__}: {exc}"

    captured_at = datetime.now(timezone.utc).isoformat()
    frozen_prices = {
        "schema": "uzi.a_qfq_daily_prices.v1",
        "captured_at_utc": captured_at,
        "source": "UZI A-share real daily source chain, qfq adjusted",
        "start": args.start,
        "benchmark": {args.benchmark.upper(): benchmark_rows},
        "bars": bars,
        "fetch_failures": failures,
        "source_by_symbol": source_by_symbol,
    }
    price_payload = {"benchmark": frozen_prices["benchmark"], "bars": bars}
    input_hash = hashlib.sha256(
        json.dumps(price_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()

    signals = _build_signals(
        bars,
        benchmark_rows,
        args.horizons,
        args.min_history,
        args.round_trip_cost_bps,
    )
    result = {
        "schema": "uzi.a_momentum_walkforward.v1",
        "captured_at_utc": captured_at,
        "source": frozen_prices["source"],
        "input_sha256": input_hash,
        "tickers": list(bars),
        "benchmark": args.benchmark.upper(),
        "start": args.start,
        "horizons": args.horizons,
        "min_history": args.min_history,
        "round_trip_cost_bps": args.round_trip_cost_bps,
        "source_by_symbol": source_by_symbol,
        "sampling": "signal at close t; entry next close; non-overlap stride=horizon per issuer",
        "fetch_failures": failures,
        "analysis": _analyze(signals, args.horizons),
        "temporal_holdouts": {
            "through_2022": _analyze(
                [row for row in signals if row["signal_date"] < "2023-01-01"], args.horizons
            ),
            "2023_onward": _analyze(
                [row for row in signals if row["signal_date"] >= "2023-01-01"], args.horizons
            ),
        },
        "signals": signals,
    }

    if args.prices_out:
        args.prices_out.parent.mkdir(parents=True, exist_ok=True)
        args.prices_out.write_text(json.dumps(frozen_prices, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_out:
        _write_markdown(result, args.markdown_out)

    print(json.dumps({
        "captured_at_utc": captured_at,
        "input_sha256": input_hash,
        "tickers": len(bars),
        "failures": failures,
        "signals": len(signals),
        "analysis": result["analysis"],
    }, ensure_ascii=False))
    return 0 if bars and signals else 1


if __name__ == "__main__":
    raise SystemExit(main())
