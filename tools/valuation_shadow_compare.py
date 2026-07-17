"""Real-data A/US/HK cash-flow normalization shadow harness.

This tool never changes production scoring or DCF inputs.  It collects annual
cash-flow evidence, compares latest values with fixed 3Y/5Y diagnostics, and
marks semantic gates (financial institution, negative FCF, currency mismatch,
or missing bridge data).  Output is an audit artifact, not an investment call.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fetch_financials import main as fetch_financials  # noqa: E402
from lib.market_router import parse_ticker  # noqa: E402


DEFAULT_TICKERS = [
    "600519.SH", "300750.SZ", "601318.SH",
    "AAPL", "AMZN", "MSTR", "JPM",
    "00700.HK", "09988.HK", "00005.HK",
]


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _is_financial(industry: object, sector: object = None) -> bool:
    text = f"{industry or ''} {sector or ''}".lower()
    return any(term in text for term in (
        "银行", "保险", "证券", "券商", "信托", "bank", "insurance",
        "capital markets", "brokerage", "financial conglomerate",
    ))


def _series(df, names: tuple[str, ...]) -> tuple[str, list[dict[str, Any]]]:
    if df is None or getattr(df, "empty", True):
        return "", []
    for name in names:
        if name not in df.index:
            continue
        rows = []
        for column in df.columns:
            value = _finite(df.at[name, column])
            if value is not None:
                rows.append({"period": str(column)[:10], "value": value})
        rows.sort(key=lambda row: row["period"])
        return name, rows
    return "", []


def _yahoo_evidence(ticker: str) -> dict[str, Any]:
    import yfinance as yf  # project dependency

    symbol = ticker
    if ticker.endswith(".HK"):
        symbol = f"{int(ticker.split('.')[0]):04d}.HK"
    elif ticker.endswith(".SH"):
        symbol = ticker.removesuffix(".SH") + ".SS"
    t = yf.Ticker(symbol)
    info = t.info or {}
    cashflow = t.cashflow
    balance = t.balance_sheet
    fcf_row, fcf = _series(cashflow, ("Free Cash Flow", "FreeCashFlow"))
    ocf_row, ocf = _series(cashflow, ("Operating Cash Flow", "Total Cash From Operating Activities"))
    capex_row, capex = _series(cashflow, ("Capital Expenditure", "Capital Expenditures"))
    debt_row, debt = _series(balance, ("Total Debt",))
    cash_row, cash = _series(balance, ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"))
    return {
        "symbol": symbol,
        "quote_currency": info.get("currency") or "",
        "statement_currency": info.get("financialCurrency") or "",
        "sector": info.get("sector") or "",
        "industry": info.get("industry") or "",
        "shares_outstanding": _finite(info.get("sharesOutstanding")),
        "current_price": _finite(info.get("currentPrice")),
        "market_cap": _finite(info.get("marketCap")),
        "fcf_row": fcf_row, "fcf": fcf,
        "ocf_row": ocf_row, "ocf": ocf,
        "capex_row": capex_row, "capex": capex,
        "debt_row": debt_row, "debt": debt,
        "cash_row": cash_row, "cash": cash,
    }


def _window(values: list[float], size: int) -> dict[str, Any] | None:
    if len(values) < size:
        return None
    sample = values[-size:]
    med = statistics.median(sample)
    deviations = [abs(value - med) for value in sample]
    return {
        "n": size,
        "median": round(med, 4),
        "mean": round(statistics.mean(sample), 4),
        "min": round(min(sample), 4),
        "max": round(max(sample), 4),
        "mad": round(statistics.median(deviations), 4),
    }


def _diagnostics(values: list[float]) -> dict[str, Any]:
    latest = values[-1] if values else None
    w3 = _window(values, 3)
    w5 = _window(values, 5)
    signs = [1 if value > 0 else -1 if value < 0 else 0 for value in values]
    switches = sum(1 for left, right in zip(signs, signs[1:]) if left != right)
    ratio3 = latest / w3["median"] if latest is not None and w3 and w3["median"] else None
    return {
        "latest": latest,
        "three_year": w3,
        "five_year": w5,
        "positive_years": sum(value > 0 for value in values),
        "negative_years": sum(value < 0 for value in values),
        "sign_switches": switches,
        "latest_to_3y_median": round(ratio3, 4) if ratio3 is not None else None,
    }


def collect_one(ticker: str) -> dict[str, Any]:
    started = time.perf_counter()
    ti = parse_ticker(ticker)
    repo = fetch_financials(ticker)
    fin = repo.get("data") or {}
    yahoo: dict[str, Any] = {}
    try:
        yahoo = _yahoo_evidence(ticker)
    except Exception as exc:
        yahoo = {"error": f"{type(exc).__name__}: {exc}"}

    periods = list(fin.get("free_cash_flow_history_years") or [])
    values = [_finite(value) for value in (fin.get("free_cash_flow_history") or [])]
    clean_values = [value for value in values if value is not None]
    source = "repo_fetch_financials"
    statement_currency = str(fin.get("free_cash_flow_currency") or "")
    basis = str(fin.get("free_cash_flow_basis") or "")
    cash_flow_class = str(fin.get("free_cash_flow_class") or "unknown")

    if ti.market == "H" and yahoo.get("fcf"):
        periods = [row["period"] for row in yahoo["fcf"]]
        clean_values = [round(float(row["value"]) / 1e8, 4) for row in yahoo["fcf"]]
        source = "yfinance_hk_shadow_supplement"
        statement_currency = str(yahoo.get("statement_currency") or "")
        basis = "yfinance_cashflow_free_cash_flow"
        cash_flow_class = "levered_cash_flow_proxy"

    industry = yahoo.get("industry") or ""
    sector = yahoo.get("sector") or ""
    quote_currency = str(yahoo.get("quote_currency") or {"A": "CNY", "H": "HKD", "U": "USD"}.get(ti.market, ""))
    diagnostics = _diagnostics(clean_values)
    latest = diagnostics["latest"]
    financial = _is_financial(industry, sector) or ticker in {"601318.SH", "00005.HK", "JPM"}
    gates = []
    if financial:
        gates.append("financial_institution_not_applicable")
    if latest is None:
        gates.append("missing_explicit_fcf")
    elif latest <= 0:
        gates.append("non_positive_latest_fcf")
    if statement_currency and quote_currency and statement_currency != quote_currency:
        gates.append("statement_quote_currency_mismatch_requires_fx")
    if diagnostics["sign_switches"]:
        gates.append("fcf_sign_instability")
    if diagnostics["latest_to_3y_median"] is not None and not 0.5 <= abs(diagnostics["latest_to_3y_median"]) <= 1.5:
        gates.append("latest_materially_differs_from_3y_median")
    production_gates = list(gates)
    if cash_flow_class != "fcff":
        production_gates.append("production_unsupported_cash_flow_class_for_enterprise_dcf")
    health = fin.get("financial_health") or {}
    if health.get("net_debt_bridge_production_eligible") is not True:
        production_gates.append("production_missing_debt_or_cash_bridge")
    if ti.market != "A":
        production_gates.append("production_discount_rate_contract_not_verified")

    return {
        "ticker": ticker,
        "market": ti.market,
        "source": source,
        "repo_source": repo.get("source"),
        "basis": basis,
        "cash_flow_class": cash_flow_class,
        "periods": periods,
        "fcf_history_yi": clean_values,
        "statement_currency": statement_currency,
        "quote_currency": quote_currency,
        "industry": industry,
        "sector": sector,
        "diagnostics": diagnostics,
        "shadow_gates": gates,
        "production_gates": production_gates,
        "production_dcf_eligible": not production_gates,
        "yahoo_bridge": {
            "shares_outstanding": yahoo.get("shares_outstanding"),
            "current_price": yahoo.get("current_price"),
            "market_cap": yahoo.get("market_cap"),
            "latest_debt": (yahoo.get("debt") or [{}])[-1] if yahoo.get("debt") else None,
            "latest_cash": (yahoo.get("cash") or [{}])[-1] if yahoo.get("cash") else None,
        },
        "elapsed_s": round(time.perf_counter() - started, 3),
        "errors": [value for value in (repo.get("error"), yahoo.get("error")) if value],
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# A/US/HK valuation shadow comparison",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        "- evidence: live project fetchers plus yfinance HK shadow supplement",
        "- boundary: diagnostic only; no production scoring or DCF input changes",
        "",
        "| ticker | market | latest | 3Y median | 5Y median | latest/3Y | currencies | canonical gate |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in payload["results"]:
        diag = row["diagnostics"]
        three = (diag.get("three_year") or {}).get("median")
        five = (diag.get("five_year") or {}).get("median")
        gate = ", ".join(row["production_gates"]) or "eligible"
        lines.append(
            f"| {row['ticker']} | {row['market']} | {diag.get('latest')} | {three} | {five} | "
            f"{diag.get('latest_to_3y_median')} | {row['statement_currency']} / {row['quote_currency']} | {gate} |"
        )
    lines.extend(["", "## Raw annual evidence", ""])
    for row in payload["results"]:
        lines.append(f"- `{row['ticker']}`: periods={row['periods']}; FCF={row['fcf_history_yi']} {row['statement_currency']} 亿")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=DEFAULT_TICKERS)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    results = [collect_one(ticker) for ticker in args.tickers]
    payload = {
        "schema_version": "uzi.valuation-shadow.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "real_data_only": True,
        "results": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "valuation-shadow.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "valuation-shadow.md").write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({
        "rows": len(results),
        "eligible": sum(row["production_dcf_eligible"] for row in results),
        "gated": sum(not row["production_dcf_eligible"] for row in results),
        "output_dir": str(args.output_dir.resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
