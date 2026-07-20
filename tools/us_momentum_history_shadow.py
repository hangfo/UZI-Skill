#!/usr/bin/env python3
"""Compare US momentum-history contracts on the same real Yahoo daily bars.

The tool fetches each symbol once, then evaluates the frozen payload in detached
baseline and candidate worktrees.  It is intentionally a fetch/indicator shadow:
it does not mutate caches, scores, valuation inputs, or trading decisions.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TICKERS = ["MU", "WDC", "STX", "SNDK", "GEV", "BMNR", "CRCL", "FIG", "SPCX"]
DEFAULT_WINDOWS = [60, 90, 120, 180, 200]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UZI-Momentum-Shadow/1.0"


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=check
    )


def _resolve_ref(ref: str) -> str:
    return _git("rev-parse", ref).stdout.strip()


def _fetch_yahoo_daily(ticker: str, range_: str = "2y") -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"interval": "1d", "range": range_, "events": "div,splits"})
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError(payload.get("chart", {}).get("error") or "empty Yahoo chart result")

    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    rows: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        closes = quote.get("close") or []
        close = closes[index] if index < len(closes) else None
        if close is None or float(close) <= 0:
            continue

        def value(key: str, default: float) -> float:
            values = quote.get(key) or []
            item = values[index] if index < len(values) else None
            return float(item) if item is not None else float(default)

        rows.append({
            "Date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
            "Open": value("open", close),
            "High": value("high", close),
            "Low": value("low", close),
            "Close": float(close),
            "Volume": value("volume", 0),
        })
    if not rows:
        raise RuntimeError("Yahoo returned no valid daily rows")
    return rows


_EVALUATOR = r"""
import json, sys, time
from pathlib import Path
worktree, payload_path, output_path = map(Path, sys.argv[1:4])
sys.path.insert(0, str(worktree / 'skills' / 'deep-analysis' / 'scripts'))
from fetch_kline import compute_indicators
payload = json.loads(payload_path.read_text(encoding='utf-8'))
timings = []
out = []
for _ in range(payload.get('repeats', 5)):
    started = time.perf_counter()
    current = []
    for ticker, rows in payload['bars'].items():
        lengths = sorted(set(payload['windows'] + [len(rows)]))
        for length in lengths:
            if length > len(rows):
                continue
            sample = rows[:length] if length < len(rows) else rows
            ind = compute_indicators(sample)
            current.append({
                'ticker': ticker,
                'window': 'full' if length == len(rows) else length,
                'rows': length,
                'as_of': sample[-1]['Date'],
                'stage': ind.get('stage'),
                'ma200': ind.get('ma200'),
                'above_ma200': ind.get('above_ma200'),
                'ma_bull_alignment': ind.get('ma_bull_alignment'),
                'year_high': ind.get('year_high'),
                'pct_from_year_high': ind.get('pct_from_year_high'),
                'history_observations': ind.get('history_observations'),
                'trend_history_sufficient': ind.get('trend_history_sufficient'),
                'year_window_complete': ind.get('year_window_complete'),
            })
    timings.append(time.perf_counter() - started)
    out = current
output_path.write_text(json.dumps({'rows': out, 'compute_seconds': timings}, ensure_ascii=False), encoding='utf-8')
"""


def _evaluate_ref(
    ref: str, payload_path: Path, temp_root: Path
) -> tuple[str, list[dict[str, Any]], float, list[float]]:
    sha = _resolve_ref(ref)
    worktree = temp_root / f"worktree-{sha[:10]}"
    output = temp_root / f"result-{sha[:10]}.json"
    _git("worktree", "add", "--detach", str(worktree), sha)
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _EVALUATOR, str(worktree), str(payload_path), str(output)],
            cwd=ROOT, text=True, capture_output=True
        )
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "indicator evaluation failed")
        evaluated = json.loads(output.read_text(encoding="utf-8"))
        return sha, evaluated["rows"], time.perf_counter() - started, evaluated["compute_seconds"]
    finally:
        _git("worktree", "remove", "--force", str(worktree), check=False)


def _same_number(left: Any, right: Any, tolerance: float = 1e-9) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return left == right


def _compare(baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base_map = {(row["ticker"], str(row["window"])): row for row in baseline}
    rows: list[dict[str, Any]] = []
    for cand in candidate:
        key = (cand["ticker"], str(cand["window"]))
        base = base_map[key]
        count = int(cand["rows"])
        violations: list[str] = []
        benefits: list[str] = []

        if count < 200:
            if cand.get("stage") != 0 or cand.get("ma200") is not None or cand.get("above_ma200") is not None:
                violations.append("candidate still exposes a mature MA200/stage signal before 200 observations")
            if base.get("stage") not in (None, 0) and cand.get("stage") == 0:
                benefits.append(f"removed baseline Stage {base.get('stage')} from incomplete history")
        elif base.get("stage") != cand.get("stage"):
            violations.append("mature-history stage changed")

        if count < 250:
            if cand.get("year_high") is not None or cand.get("pct_from_year_high") is not None:
                violations.append("candidate still exposes a 52-week value before 250 observations")
            if base.get("pct_from_year_high") is not None and cand.get("pct_from_year_high") is None:
                benefits.append("removed incomplete 52-week precision")
        else:
            for field in ("year_high", "pct_from_year_high"):
                if not _same_number(base.get(field), cand.get(field)):
                    violations.append(f"mature-history {field} changed")

        verdict = "possible_regression" if violations else ("beneficial_contract_fix" if benefits else "no_change")
        rows.append({
            "ticker": cand["ticker"],
            "window": cand["window"],
            "rows": count,
            "as_of": cand["as_of"],
            "baseline_stage": base.get("stage"),
            "candidate_stage": cand.get("stage"),
            "baseline_ma200": base.get("ma200"),
            "candidate_ma200": cand.get("ma200"),
            "baseline_pct_from_year_high": base.get("pct_from_year_high"),
            "candidate_pct_from_year_high": cand.get("pct_from_year_high"),
            "verdict": verdict,
            "benefits": benefits,
            "violations": violations,
        })
    return rows


def _markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# US momentum history shadow",
        "",
        f"- fetched_at_utc: `{result['fetched_at_utc']}`",
        f"- baseline: `{result['baseline']}`",
        f"- candidate: `{result['candidate']}`",
        f"- real tickers: `{', '.join(result['tickers'])}`",
        f"- rows: `{summary['total']}`; no_change `{summary['no_change']}`; beneficial_contract_fix `{summary['beneficial_contract_fix']}`; possible_regression `{summary['possible_regression']}`",
        f"- process seconds: baseline `{result['timing_seconds']['baseline_process']:.3f}`, candidate `{result['timing_seconds']['candidate_process']:.3f}`",
        f"- pure-compute median seconds: baseline `{result['timing_seconds']['baseline_compute_median']:.6f}`, candidate `{result['timing_seconds']['candidate_compute_median']:.6f}`; warning `{result['performance_warning']}`",
        "",
        "| ticker | window | as of | baseline stage | candidate stage | verdict |",
        "|---|---:|---|---:|---:|---|",
    ]
    for row in result["rows"]:
        lines.append(
            f"| {row['ticker']} | {row['window']} | {row['as_of']} | {row['baseline_stage']} | {row['candidate_stage']} | {row['verdict']} |"
        )
    lines.extend([
        "",
        "The bars are real Yahoo daily observations fetched once and replayed identically in both worktrees. Short windows are historical snapshots of those real series, not generated prices.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--windows", nargs="+", type=int, default=DEFAULT_WINDOWS)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    bars: dict[str, list[dict[str, Any]]] = {}
    for ticker in args.tickers:
        bars[ticker.upper()] = _fetch_yahoo_daily(ticker.upper())

    temp_base = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix="uzi-us-momentum-shadow-") as temp_name:
        temp_root = Path(temp_name).resolve()
        if temp_root.parent != temp_base or not temp_root.name.startswith("uzi-us-momentum-shadow-"):
            raise RuntimeError(f"unexpected temp path: {temp_root}")
        payload_path = temp_root / "real-bars.json"
        payload_path.write_text(
            json.dumps({"bars": bars, "windows": args.windows, "repeats": max(1, args.repeats)}),
            encoding="utf-8",
        )
        baseline_sha, baseline_rows, baseline_seconds, baseline_compute = _evaluate_ref(
            args.baseline, payload_path, temp_root
        )
        candidate_sha, candidate_rows, candidate_seconds, candidate_compute = _evaluate_ref(
            args.candidate, payload_path, temp_root
        )

    rows = _compare(baseline_rows, candidate_rows)
    summary = {
        "total": len(rows),
        "no_change": sum(row["verdict"] == "no_change" for row in rows),
        "beneficial_contract_fix": sum(row["verdict"] == "beneficial_contract_fix" for row in rows),
        "possible_regression": sum(row["verdict"] == "possible_regression" for row in rows),
    }
    baseline_median = statistics.median(baseline_compute)
    candidate_median = statistics.median(candidate_compute)
    performance_warning = (
        candidate_median > baseline_median * 1.15
        and candidate_median - baseline_median > 0.01
    )
    result = {
        "schema_version": "uzi.us_momentum_history_shadow.v1",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": baseline_sha,
        "candidate": candidate_sha,
        "tickers": list(bars),
        "source": "Yahoo Finance chart v8 real daily bars",
        "timing_seconds": {
            "baseline_process": baseline_seconds,
            "candidate_process": candidate_seconds,
            "baseline_compute_runs": baseline_compute,
            "candidate_compute_runs": candidate_compute,
            "baseline_compute_median": baseline_median,
            "candidate_compute_median": candidate_median,
        },
        "performance_warning": performance_warning,
        "summary": summary,
        "rows": rows,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 1 if summary["possible_regression"] or performance_warning else 0


if __name__ == "__main__":
    raise SystemExit(main())
