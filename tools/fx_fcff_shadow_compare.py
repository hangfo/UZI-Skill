"""Real-data FX and FCFF reconstruction shadow audit.

This tool is deliberately outside the production scoring and valuation path.
It checks whether timestamped FX contracts and two independent FCFF
reconstruction paths agree well enough to justify later productization.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yfinance as yf
import requests

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TICKERS = (
    ("600519.SH", "600519.SS", "A", False),
    ("300750.SZ", "300750.SZ", "A", False),
    ("601318.SH", "601318.SS", "A", True),
    ("AAPL", "AAPL", "U", False),
    ("AMZN", "AMZN", "U", False),
    ("MSTR", "MSTR", "U", False),
    ("BABA", "BABA", "U", False),
    ("JPM", "JPM", "U", True),
    ("00700.HK", "0700.HK", "H", False),
    ("09988.HK", "9988.HK", "H", False),
    ("00005.HK", "0005.HK", "H", True),
)

FX_CONTRACTS = (
    {"base": "CNY", "quote": "HKD", "direct": "CNYHKD=X", "inverse": "HKDCNY=X",
     "triangle": ("CNYUSD=X", "USDHKD=X")},
    {"base": "CNY", "quote": "USD", "direct": "CNYUSD=X", "inverse": "USDCNY=X",
     "triangle": ("CNYHKD=X", "HKDUSD=X")},
    {"base": "USD", "quote": "HKD", "direct": "USDHKD=X", "inverse": "HKDUSD=X",
     "triangle": ("USDCNY=X", "CNYHKD=X")},
)


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _gap_pct(left: float | None, right: float | None) -> float | None:
    if left is None or right is None or max(abs(left), abs(right)) == 0:
        return None
    return abs(left - right) / max(abs(left), abs(right)) * 100


def validate_fx_contract(
    *, direct_rate: float | None, inverse_rate: float | None,
    triangle_rate: float | None, as_of: str, today: date | None = None,
    inverse_limit_pct: float = 0.5, triangle_limit_pct: float = 0.75,
    stale_limit_days: int = 3,
    official_rate: float | None = None,
    official_market_rate: float | None = None,
    official_as_of: str = "",
    official_limit_pct: float = 0.75,
) -> dict[str, Any]:
    """Validate market identities plus an independent official observation."""
    current = today or datetime.now(timezone.utc).date()
    gates = []
    if direct_rate is None or direct_rate <= 0:
        gates.append("missing_or_nonpositive_direct_rate")
    if inverse_rate is None or inverse_rate <= 0:
        gates.append("missing_or_nonpositive_inverse_rate")
    implied_from_inverse = 1 / inverse_rate if inverse_rate and inverse_rate > 0 else None
    inverse_gap = _gap_pct(direct_rate, implied_from_inverse)
    triangle_gap = _gap_pct(direct_rate, triangle_rate)
    try:
        stale_days = (current - date.fromisoformat(as_of[:10])).days
    except (TypeError, ValueError):
        stale_days = None
        gates.append("invalid_or_missing_as_of")
    if stale_days is not None and (stale_days < 0 or stale_days > stale_limit_days):
        gates.append("stale_or_future_fx_observation")
    if inverse_gap is None or inverse_gap > inverse_limit_pct:
        gates.append("inverse_identity_gap")
    if triangle_gap is None or triangle_gap > triangle_limit_pct:
        gates.append("triangle_cross_gap")
    official_gap = _gap_pct(official_market_rate, official_rate)
    try:
        official_stale_days = (current - date.fromisoformat(official_as_of[:10])).days
    except (TypeError, ValueError):
        official_stale_days = None
        gates.append("invalid_or_missing_official_as_of")
    if official_rate is None or official_rate <= 0:
        gates.append("missing_or_nonpositive_official_rate")
    if official_market_rate is None or official_market_rate <= 0:
        gates.append("missing_same_date_market_rate")
    if official_stale_days is not None and (
        official_stale_days < 0 or official_stale_days > stale_limit_days
    ):
        gates.append("stale_or_future_official_observation")
    if official_gap is None or official_gap > official_limit_pct:
        gates.append("official_cross_source_gap")
    return {
        "eligible": not gates,
        "gates": gates,
        "implied_from_inverse": implied_from_inverse,
        "inverse_gap_pct": round(inverse_gap, 6) if inverse_gap is not None else None,
        "triangle_gap_pct": round(triangle_gap, 6) if triangle_gap is not None else None,
        "official_gap_pct": round(official_gap, 6) if official_gap is not None else None,
        "stale_days": stale_days,
        "official_stale_days": official_stale_days,
    }


def reconstruct_fcff(components: dict[str, Any]) -> dict[str, Any]:
    """Compare two FCFF paths without pretending either is canonical.

    Path A is a partial EBIT bridge.  It can miss non-cash items beyond D&A.
    Path B adds after-tax interest to provider levered FCF.  It depends on the
    accounting policy classifying interest inside operating cash flow.
    """
    ebit = _finite(components.get("ebit"))
    tax = _finite(components.get("tax_provision"))
    pretax = _finite(components.get("pretax_income"))
    da = _finite(components.get("depreciation_amortization"))
    capex = _finite(components.get("signed_capex"))
    change_wc = _finite(components.get("change_working_capital"))
    levered_fcf = _finite(components.get("levered_fcf"))
    interest = _finite(components.get("interest_expense"))
    gates = []
    tax_rate = tax / pretax if tax is not None and pretax is not None and pretax > 0 else None
    if tax_rate is None or not 0 <= tax_rate <= 0.50:
        gates.append("invalid_effective_tax_rate")
    partial_inputs = (ebit, tax_rate, da, capex, change_wc)
    partial = (
        ebit * (1 - tax_rate) + da + capex + change_wc
        if all(value is not None for value in partial_inputs) else None
    )
    interest_bridge = (
        levered_fcf + interest * (1 - tax_rate)
        if None not in (levered_fcf, interest, tax_rate) else None
    )
    if partial is None:
        gates.append("partial_ebit_bridge_incomplete")
    if interest_bridge is None:
        gates.append("after_tax_interest_bridge_incomplete")
    method_gap = _gap_pct(partial, interest_bridge)
    if method_gap is None or method_gap > 10:
        gates.append("fcff_methods_gap_gt_10pct")
    if partial is not None and partial <= 0:
        gates.append("nonpositive_partial_fcff")
    if interest_bridge is not None and interest_bridge <= 0:
        gates.append("nonpositive_interest_bridge_fcff")
    # This must be proved from the issuer accounting policy, not inferred from
    # market or provider labels.  Keep production closed in this shadow tool.
    gates.append("interest_cashflow_classification_unverified")
    return {
        "effective_tax_rate": round(tax_rate, 8) if tax_rate is not None else None,
        "partial_ebit_bridge": partial,
        "after_tax_interest_bridge": interest_bridge,
        "method_gap_pct": round(method_gap, 4) if method_gap is not None else None,
        "gates": list(dict.fromkeys(gates)),
        "production_eligible": False,
    }


def _latest_common_fx(symbols: tuple[str, ...]) -> tuple[str, dict[str, float], dict[str, list[dict[str, Any]]]]:
    series = {}
    histories = {}
    for symbol in symbols:
        frame = yf.Ticker(symbol).history(period="10d", interval="1d", auto_adjust=False)
        close = frame["Close"] if frame is not None and "Close" in frame else None
        observations = [
            {"date": str(index)[:10], "close": float(value)}
            for index, value in (close.dropna().items() if close is not None else ())
            if _finite(value) is not None
        ]
        histories[symbol] = observations
        series[symbol] = {row["date"]: row["close"] for row in observations}
    common_dates = set.intersection(*(set(values) for values in series.values())) if series else set()
    if not common_dates:
        return "", {}, histories
    as_of = max(common_dates)
    return as_of, {symbol: values[as_of] for symbol, values in series.items()}, histories


def collect_official_fx() -> dict[str, Any]:
    """Fetch latest ECB reference crosses plus HKMA's latest published row."""
    ecb_url = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD+CNY+HKD.EUR.SP00.A"
    response = requests.get(
        ecb_url,
        params={"lastNObservations": 5, "format": "csvdata"},
        timeout=30,
    )
    response.raise_for_status()
    ecb_rows = list(csv.DictReader(io.StringIO(response.text)))
    by_date: dict[str, dict[str, float]] = {}
    for row in ecb_rows:
        value = _finite(row.get("OBS_VALUE"))
        if value is not None:
            by_date.setdefault(row["TIME_PERIOD"], {})[row["CURRENCY"]] = value
    complete_dates = [day for day, values in by_date.items() if {"USD", "CNY", "HKD"} <= values.keys()]
    ecb_as_of = max(complete_dates) if complete_dates else ""
    values = by_date.get(ecb_as_of, {})
    ecb_rates = {}
    if values:
        ecb_rates = {
            "CNY/HKD": values["HKD"] / values["CNY"],
            "CNY/USD": values["USD"] / values["CNY"],
            "USD/HKD": values["HKD"] / values["USD"],
        }

    hkma_url = (
        "https://api.hkma.gov.hk/public/market-data-and-statistics/"
        "monthly-statistical-bulletin/er-ir/er-eeri-daily"
    )
    hkma_response = requests.get(hkma_url, params={"offset": 0}, timeout=30)
    hkma_response.raise_for_status()
    records = hkma_response.json().get("result", {}).get("records", [])
    latest = max(records, key=lambda item: item.get("end_of_day", ""), default={})
    hkma_rates = {}
    usd = _finite(latest.get("usd"))
    cny = _finite(latest.get("cny"))
    if usd and cny:
        hkma_rates = {"CNY/HKD": cny, "CNY/USD": cny / usd, "USD/HKD": usd}
    hkma_as_of = latest.get("end_of_day", "")
    try:
        hkma_stale_days = (datetime.now(timezone.utc).date() - date.fromisoformat(hkma_as_of)).days
    except (TypeError, ValueError):
        hkma_stale_days = None
    return {
        "ecb": {
            "as_of": ecb_as_of,
            "rates": ecb_rates,
            "source": "ECB euro foreign exchange reference rates",
            "url": str(response.url),
        },
        "hkma": {
            "as_of": hkma_as_of,
            "stale_days": hkma_stale_days,
            "rates": hkma_rates,
            "source": "HKMA daily exchange rates",
            "url": str(hkma_response.url),
            "freshness_role": "reference_only; not an eligibility gate when publication lags",
        },
    }


def collect_fx(official: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for contract in FX_CONTRACTS:
        symbols = (contract["direct"], contract["inverse"], *contract["triangle"])
        as_of, rates, histories = _latest_common_fx(symbols)
        direct = rates.get(contract["direct"])
        inverse = rates.get(contract["inverse"])
        triangle = rates.get(contract["triangle"][0])
        triangle_second = rates.get(contract["triangle"][1])
        triangle_rate = triangle * triangle_second if triangle and triangle_second else None
        pair = f"{contract['base']}/{contract['quote']}"
        official_as_of = official["ecb"]["as_of"]
        direct_by_date = {
            row["date"]: row["close"] for row in histories[contract["direct"]]
        }
        validation = validate_fx_contract(
            direct_rate=direct, inverse_rate=inverse,
            triangle_rate=triangle_rate, as_of=as_of,
            official_rate=official["ecb"]["rates"].get(pair),
            official_market_rate=direct_by_date.get(official_as_of),
            official_as_of=official_as_of,
        )
        direct_history = [row["close"] for row in histories[contract["direct"]]][-5:]
        validation["five_observation_range_pct"] = (
            round((max(direct_history) - min(direct_history)) / statistics.median(direct_history) * 100, 6)
            if len(direct_history) >= 2 and statistics.median(direct_history) else None
        )
        rows.append({
            **contract,
            "as_of": as_of,
            "direct_rate": direct,
            "inverse_rate": inverse,
            "triangle_rate": triangle_rate,
            "official_rate": official["ecb"]["rates"].get(pair),
            "official_as_of": official_as_of,
            "official_same_date_market_rate": direct_by_date.get(official_as_of),
            "hkma_reference_rate": official["hkma"]["rates"].get(pair),
            "hkma_reference_as_of": official["hkma"]["as_of"],
            "validation": validation,
            "histories": histories,
            "source": "Yahoo Finance daily FX close",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        })
    return rows


def _row_value(frame, row_names: tuple[str, ...], period) -> tuple[str, float | None]:
    if frame is None or getattr(frame, "empty", True):
        return "", None
    row_name = next((name for name in row_names if name in frame.index), None)
    if not row_name or period not in frame.columns:
        return "", None
    return row_name, _finite(frame.at[row_name, period])


def collect_fcff_one(ticker: str, symbol: str, market: str, financial: bool) -> dict[str, Any]:
    started = time.perf_counter()
    provider = yf.Ticker(symbol)
    info = provider.info or {}
    income = provider.financials
    cashflow = provider.cashflow
    common = sorted(set(income.columns) & set(cashflow.columns)) if not income.empty and not cashflow.empty else []
    period = common[-1] if common else None
    field_specs = {
        "ebit": (income, ("EBIT",)),
        "tax_provision": (income, ("Tax Provision",)),
        "pretax_income": (income, ("Pretax Income",)),
        "interest_expense": (income, ("Interest Expense", "Interest Expense Non Operating")),
        "depreciation_amortization": (cashflow, ("Depreciation And Amortization", "Depreciation")),
        "signed_capex": (cashflow, ("Capital Expenditure", "Capital Expenditures")),
        "change_working_capital": (cashflow, ("Change In Working Capital",)),
        "levered_fcf": (cashflow, ("Free Cash Flow", "FreeCashFlow")),
    }
    components = {}
    source_fields = {}
    for key, (frame, names) in field_specs.items():
        source_fields[key], components[key] = _row_value(frame, names, period)
    result = reconstruct_fcff(components)
    if financial:
        result["gates"].insert(0, "financial_institution_not_applicable")
    statement_currency = str(info.get("financialCurrency") or "")
    quote_currency = str(info.get("currency") or "")
    if statement_currency and quote_currency and statement_currency != quote_currency:
        result["gates"].append("statement_quote_currency_mismatch_requires_fx")
    result["gates"] = list(dict.fromkeys(result["gates"]))
    return {
        "ticker": ticker,
        "symbol": symbol,
        "market": market,
        "financial_institution": financial,
        "period": str(period)[:10] if period is not None else "",
        "statement_currency": statement_currency,
        "quote_currency": quote_currency,
        "components": components,
        "source_fields": source_fields,
        "reconstruction": result,
        "source": "Yahoo Finance annual financials/cashflow",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.perf_counter() - started, 3),
    }


def collect() -> dict[str, Any]:
    official_fx = collect_official_fx()
    fx_rows = collect_fx(official_fx)
    fcff_rows = [collect_fcff_one(*item) for item in TICKERS]
    return {
        "schema_version": "uzi.fx-fcff-shadow.v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "real_data_only": True,
        "production_mutation": False,
        "fx": fx_rows,
        "official_fx_sources": official_fx,
        "fcff": fcff_rows,
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Timestamped FX and FCFF reconstruction shadow", "",
        f"- generated_at: `{payload['generated_at']}`",
        "- boundary: real observations only; no scoring, WACC, growth or production DCF mutation", "",
        f"- ECB official reference as-of: `{payload['official_fx_sources']['ecb']['as_of']}`",
        f"- HKMA official reference as-of: `{payload['official_fx_sources']['hkma']['as_of']}` "
        f"(lag `{payload['official_fx_sources']['hkma']['stale_days']}` days; reference-only)", "",
        "## FX contracts", "",
        "| pair | market as-of | direct | official as-of | official gap | inverse gap | triangle gap | 5-observation range | eligible | gates |",
        "|---|---|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for row in payload["fx"]:
        v = row["validation"]
        lines.append(
            f"| {row['base']}/{row['quote']} | {row['as_of']} | {row['direct_rate']} | "
            f"{row['official_as_of']} | {v['official_gap_pct']}% | {v['inverse_gap_pct']}% | "
            f"{v['triangle_gap_pct']}% | {v['five_observation_range_pct']}% | "
            f"{v['eligible']} | {', '.join(v['gates']) or '-'} |"
        )
    lines += ["", "## FCFF reconstruction", "",
              "| ticker | period | currencies | partial EBIT bridge | FCF + after-tax interest | gap | gates |",
              "|---|---|---|---:|---:|---:|---|"]
    for row in payload["fcff"]:
        r = row["reconstruction"]
        lines.append(
            f"| {row['ticker']} | {row['period']} | {row['statement_currency']}/{row['quote_currency']} | "
            f"{r['partial_ebit_bridge']} | {r['after_tax_interest_bridge']} | {r['method_gap_pct']}% | "
            f"{', '.join(r['gates'])} |"
        )
    lines += ["", "## Decision", "",
              "- FX observations may be suitable for a future explicit bridge only when freshness, inverse identity, triangulation and same-date ECB cross-source agreement all pass.",
              "- HKMA remains a second official reference, but publication lag is recorded and never hidden or used to waive freshness.",
              "- FCFF is not promoted: provider row availability does not prove interest cash-flow classification, and method disagreement is material for several issuers.",
              "- Static WACC, growth, tax-rate clamping and market-wide defaults remain rejected."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    payload = collect()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "fx-fcff-shadow.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "fx-fcff-shadow.md").write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({
        "fx_contracts": len(payload["fx"]),
        "fx_eligible": sum(row["validation"]["eligible"] for row in payload["fx"]),
        "fcff_rows": len(payload["fcff"]),
        "fcff_production_eligible": sum(row["reconstruction"]["production_eligible"] for row in payload["fcff"]),
        "output_dir": str(args.output_dir.resolve()),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
