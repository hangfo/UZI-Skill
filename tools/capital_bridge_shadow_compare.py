"""Cross-market real-statement capital bridge shadow audit.

The output is diagnostic evidence only.  It never mutates cache, scoring, or
valuation inputs.  Definitions are kept separate when providers disagree
(strict cash vs cash plus deposits/investments; reported debt vs lease debt).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import akshare as ak
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fetch_financials import main as fetch_financials  # noqa: E402

A_TICKERS = ("600519.SH", "300750.SZ", "601318.SH")
US_TICKERS = ("AAPL", "AMZN", "MSTR", "JPM")
HK_TICKERS = ("00700.HK", "09988.HK", "00005.HK")
FINANCIALS = {"601318.SH", "JPM", "00005.HK"}
USER_AGENT = "UZI-Skill real-data validation hangfo@users.noreply.github.com"
# Stable SEC registrant identifiers; facts themselves are always fetched live.
SEC_CIK = {"AAPL": 320193, "AMZN": 1018724, "MSTR": 1050446, "JPM": 19617}


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _series(df, names: tuple[str, ...]) -> tuple[str, list[dict[str, Any]]]:
    if df is None or getattr(df, "empty", True):
        return "", []
    field = next((name for name in names if name in df.index), None)
    if not field:
        return "", []
    rows = []
    for column in df.columns:
        value = _finite(df.at[field, column])
        if value is not None:
            rows.append({"period": str(column)[:10], "value": value})
    rows.sort(key=lambda row: row["period"])
    return field, rows


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return rows[-1] if rows else None


def _gap(left: float | None, right: float | None) -> float | None:
    if left is None or right is None or max(abs(left), abs(right)) == 0:
        return None
    return round(abs(left - right) / max(abs(left), abs(right)) * 100, 2)


def _yahoo(symbol: str) -> dict[str, Any]:
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    balance = ticker.balance_sheet
    cashflow = ticker.cashflow
    debt_field, debt = _series(balance, ("Total Debt", "TotalDebt"))
    strict_cash_field, strict_cash = _series(
        balance, ("Cash And Cash Equivalents", "CashAndCashEquivalents")
    )
    broad_cash_field, broad_cash = _series(
        balance,
        ("Cash Cash Equivalents And Short Term Investments", "CashCashEquivalentsAndShortTermInvestments"),
    )
    fcf_field, fcf = _series(cashflow, ("Free Cash Flow", "FreeCashFlow"))
    ocf_field, ocf = _series(cashflow, ("Operating Cash Flow", "Total Cash From Operating Activities"))
    capex_field, capex = _series(cashflow, ("Capital Expenditure", "Capital Expenditures"))
    return {
        "quote_currency": info.get("currency") or "",
        "statement_currency": info.get("financialCurrency") or "",
        "shares": _finite(info.get("sharesOutstanding")),
        "debt": {"field": debt_field, "latest": _latest(debt)},
        "cash_strict": {"field": strict_cash_field, "latest": _latest(strict_cash)},
        "cash_broad": {"field": broad_cash_field, "latest": _latest(broad_cash)},
        "fcf": {"field": fcf_field, "latest": _latest(fcf)},
        "ocf": {"field": ocf_field, "latest": _latest(ocf)},
        "capex": {"field": capex_field, "latest": _latest(capex)},
    }


def _sina_a_balance(ticker: str) -> dict[str, Any]:
    code, suffix = ticker.split(".")
    symbol = ("sh" if suffix == "SH" else "sz") + code
    df = ak.stock_financial_report_sina(stock=symbol, symbol="\u8d44\u4ea7\u8d1f\u503a\u8868")
    report_dates = df["\u62a5\u544a\u65e5"].astype(str)
    annual = df[report_dates.str.endswith("1231") | report_dates.str.slice(0, 10).str.endswith("12-31")].copy()
    annual = annual.sort_values("\u62a5\u544a\u65e5")
    if annual.empty:
        return {"error": "no_annual_balance_sheet"}
    row = annual.iloc[-1]
    cash = _finite(row.get("\u8d27\u5e01\u8d44\u91d1"))
    components = {}
    for field in (
        "\u77ed\u671f\u501f\u6b3e", "\u5e94\u4ed8\u77ed\u671f\u503a\u5238", "\u4e00\u5e74\u5185\u5230\u671f\u7684\u975e\u6d41\u52a8\u8d1f\u503a",
        "\u957f\u671f\u501f\u6b3e", "\u5e94\u4ed8\u503a\u5238", "\u79df\u8d41\u8d1f\u503a",
    ):
        value = _finite(row.get(field))
        if value is not None:
            components[field] = value
    return {
        "period": str(row["\u62a5\u544a\u65e5"])[:10],
        "currency": str(row.get("\u5e01\u79cd") or "CNY"),
        "cash_strict": cash,
        "debt_including_leases": sum(components.values()) if components else None,
        "debt_components": components,
    }


def _a_provider_fcf_per_share(ticker: str) -> dict[str, Any]:
    code = ticker.split(".")[0]
    df = ak.stock_financial_abstract(symbol=code)
    result = {}
    for label, key in (
        ("provider_fcff_per_share", "\u6bcf\u80a1\u4f01\u4e1a\u81ea\u7531\u73b0\u91d1\u6d41\u91cf"),
        ("provider_fcfe_per_share", "\u6bcf\u80a1\u80a1\u4e1c\u81ea\u7531\u73b0\u91d1\u6d41\u91cf"),
    ):
        row = df[df["\u6307\u6807"].astype(str) == key]
        observations = []
        if not row.empty:
            for column in df.columns:
                value = _finite(row[column].iloc[0])
                if str(column).endswith("1231") and value is not None:
                    observations.append({"period": str(column), "value": value})
        observations.sort(key=lambda item: item["period"])
        result[label] = _latest(observations)
    return result


def _sec_latest_fact(facts: dict[str, Any], concepts: tuple[str, ...]) -> dict[str, Any] | None:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        units = us_gaap.get(concept, {}).get("units", {})
        rows = units.get("USD", [])
        annual = [row for row in rows if row.get("form") == "10-K" and row.get("fp") == "FY"]
        if annual:
            annual.sort(key=lambda row: (str(row.get("end", "")), str(row.get("filed", ""))))
            row = annual[-1]
            return {
                "concept": concept,
                "period": row.get("end"),
                "filed": row.get("filed"),
                "value": _finite(row.get("val")),
            }
    return None


def _sec_us(ticker: str, cik_map: dict[str, int]) -> dict[str, Any]:
    cik = cik_map[ticker]
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    facts = response.json()
    cash = _sec_latest_fact(facts, ("CashAndCashEquivalentsAtCarryingValue",))
    ocf = _sec_latest_fact(facts, ("NetCashProvidedByUsedInOperatingActivities",))
    capex = _sec_latest_fact(facts, ("PaymentsToAcquirePropertyPlantAndEquipment",))
    debt_current = _sec_latest_fact(
        facts, ("LongTermDebtCurrent", "LongTermDebtAndFinanceLeaseObligationsCurrent", "ShortTermBorrowings")
    )
    debt_noncurrent = _sec_latest_fact(
        facts, ("LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent")
    )
    debt_parts = [item for item in (debt_current, debt_noncurrent) if item and item["value"] is not None]
    same_debt_period = len({item["period"] for item in debt_parts}) == 1 if debt_parts else False
    fcf = None
    if ocf and capex and ocf["period"] == capex["period"]:
        fcf = {"period": ocf["period"], "value": ocf["value"] - capex["value"]}
    return {
        "cik": cik,
        "source_url": url,
        "cash_strict": cash,
        "ocf": ocf,
        "capex": capex,
        "fcf_proxy": fcf,
        "debt_components": debt_parts,
        "debt_core": {
            "period": debt_parts[0]["period"] if same_debt_period else "",
            "value": sum(item["value"] for item in debt_parts) if same_debt_period else None,
        },
    }


def _us_em(ticker: str) -> dict[str, Any]:
    """Eastmoney standardized US statements used when SEC blocks this host."""
    balance = ak.stock_financial_us_report_em(stock=ticker, symbol="\u8d44\u4ea7\u8d1f\u503a\u8868")
    cashflow = ak.stock_financial_us_report_em(stock=ticker, symbol="\u73b0\u91d1\u6d41\u91cf\u8868")
    period = sorted(set(str(value)[:10] for value in balance["REPORT_DATE"]))[-1]
    b = balance[balance["REPORT_DATE"].astype(str).str.startswith(period)]
    c = cashflow[cashflow["REPORT_DATE"].astype(str).str.startswith(period)]

    def amount(frame, name: str) -> float | None:
        rows = frame[frame["ITEM_NAME"].astype(str) == name]
        return _finite(rows["AMOUNT"].iloc[0]) if not rows.empty else None

    cash = amount(b, "\u73b0\u91d1\u53ca\u73b0\u91d1\u7b49\u4ef7\u7269") or amount(b, "\u73b0\u91d1\u53ca\u5b58\u653e\u540c\u4e1a\u6b3e\u9879")
    debt_names = (
        "\u77ed\u671f\u503a\u52a1", "\u957f\u671f\u8d1f\u503a(\u672c\u671f\u90e8\u5206)", "\u957f\u671f\u8d1f\u503a", "\u501f\u6b3e",
        "\u8d44\u672c\u79df\u8d41\u503a\u52a1(\u975e\u6d41\u52a8)",
    )
    debt_components = {name: value for name in debt_names if (value := amount(b, name)) is not None}
    ocf = amount(c, "\u7ecf\u8425\u6d3b\u52a8\u4ea7\u751f\u7684\u73b0\u91d1\u6d41\u91cf\u51c0\u989d")
    signed_capex = amount(c, "\u8d2d\u4e70\u56fa\u5b9a\u8d44\u4ea7")
    return {
        "period": period,
        "cash_strict": cash,
        "debt_including_leases": sum(debt_components.values()) if debt_components else None,
        "debt_components": debt_components,
        "ocf": ocf,
        "signed_capex": signed_capex,
        "fcf_proxy": ocf + signed_capex if ocf is not None and signed_capex is not None else None,
    }


def _hk_em(ticker: str) -> dict[str, Any]:
    code = ticker.split(".")[0]
    balance = ak.stock_financial_hk_report_em(stock=code, symbol="\u8d44\u4ea7\u8d1f\u503a\u8868")
    cashflow = ak.stock_financial_hk_report_em(stock=code, symbol="\u73b0\u91d1\u6d41\u91cf\u8868")
    period = sorted(set(str(value)[:10] for value in balance["REPORT_DATE"]))[-1]
    b = balance[balance["REPORT_DATE"].astype(str).str.startswith(period)]
    c = cashflow[cashflow["REPORT_DATE"].astype(str).str.startswith(period)]

    def amount(frame, name: str) -> float | None:
        rows = frame[frame["STD_ITEM_NAME"].astype(str) == name]
        return _finite(rows["AMOUNT"].iloc[0]) if not rows.empty else None

    strict_cash = amount(b, "\u73b0\u91d1\u53ca\u7b49\u4ef7\u7269") or amount(b, "\u5e93\u5b58\u73b0\u91d1\u53ca\u77ed\u671f\u8d44\u91d1")
    deposits = [amount(b, name) for name in ("\u77ed\u671f\u5b58\u6b3e", "\u4e2d\u957f\u671f\u5b58\u6b3e", "\u53d7\u9650\u5236\u5b58\u6b3e\u53ca\u73b0\u91d1")]
    debt_names = (
        "\u77ed\u671f\u8d37\u6b3e", "\u957f\u671f\u8d37\u6b3e", "\u53ef\u8f6c\u6362\u7968\u636e\u53ca\u503a\u5238", "\u5e94\u4ed8\u7968\u636e(\u975e\u6d41\u52a8)",
        "\u878d\u8d44\u79df\u8d41\u8d1f\u503a(\u6d41\u52a8)", "\u878d\u8d44\u79df\u8d41\u8d1f\u503a(\u975e\u6d41\u52a8)", "\u5df2\u53d1\u884c\u503a\u5238",
    )
    debt_components = {name: value for name in debt_names if (value := amount(b, name)) is not None}
    ocf = amount(c, "\u7ecf\u8425\u4e1a\u52a1\u73b0\u91d1\u51c0\u989d")
    capex = amount(c, "\u8d2d\u5efa\u56fa\u5b9a\u8d44\u4ea7")
    return {
        "period": period,
        "cash_strict": strict_cash,
        "cash_broad_including_deposits": (strict_cash or 0) + sum(value for value in deposits if value is not None),
        "deposit_components": [value for value in deposits if value is not None],
        "debt_including_leases": sum(debt_components.values()) if debt_components else None,
        "debt_components": debt_components,
        "fcf_proxy": ocf - capex if ocf is not None and capex is not None else None,
        "ocf": ocf,
        "capex": capex,
    }


def collect() -> dict[str, Any]:
    rows = []
    for ticker in (*A_TICKERS, *US_TICKERS, *HK_TICKERS):
        started = time.perf_counter()
        market = "A" if ticker in A_TICKERS else "U" if ticker in US_TICKERS else "H"
        if market == "A":
            yahoo_symbol = ticker.replace(".SH", ".SS")
        elif market == "H":
            yahoo_symbol = f"{int(ticker.split('.')[0]):04d}.HK"
        else:
            yahoo_symbol = ticker
        yahoo = _yahoo(yahoo_symbol)
        row: dict[str, Any] = {
            "ticker": ticker,
            "market": market,
            "financial_institution": ticker in FINANCIALS,
            "yahoo": yahoo,
            "gates": [],
        }
        if market == "A":
            row["sina_balance"] = _sina_a_balance(ticker)
            row["provider_fcf_per_share"] = _a_provider_fcf_per_share(ticker)
            repo = (fetch_financials(ticker).get("data") or {})
            row["repo_fcf_proxy"] = {
                "period": repo.get("free_cash_flow_period"),
                "value": _finite(repo.get("free_cash_flow_yi")) * 1e8 if _finite(repo.get("free_cash_flow_yi")) is not None else None,
                "cash_flow_class": repo.get("free_cash_flow_class"),
            }
            shares = yahoo.get("shares")
            repo_fcf = row["repo_fcf_proxy"]["value"]
            row["provider_vs_repo_fcf_gap_pct"] = {}
            for key, observation in row["provider_fcf_per_share"].items():
                provider_total = observation["value"] * shares if observation and shares else None
                row["provider_vs_repo_fcf_gap_pct"][key] = _gap(provider_total, repo_fcf)
            second = row["sina_balance"]
            row["cross_source_gaps_pct"] = {
                "debt": _gap((yahoo["debt"]["latest"] or {}).get("value"), second.get("debt_including_leases")),
                "cash_strict": _gap((yahoo["cash_strict"]["latest"] or {}).get("value"), second.get("cash_strict")),
            }
        elif market == "U":
            try:
                row["sec"] = _sec_us(ticker, SEC_CIK)
            except Exception as exc:
                row["sec_error"] = f"{type(exc).__name__}: {exc}"
                row["gates"].append("sec_companyfacts_blocked_on_current_network")
            row["eastmoney_us"] = _us_em(ticker)
            second = row["eastmoney_us"]
            row["cross_source_gaps_pct"] = {
                "debt": _gap((yahoo["debt"]["latest"] or {}).get("value"), second.get("debt_including_leases")),
                "cash_strict": _gap((yahoo["cash_strict"]["latest"] or {}).get("value"), second.get("cash_strict")),
                "fcf_proxy": _gap((yahoo["fcf"]["latest"] or {}).get("value"), second.get("fcf_proxy")),
            }
        else:
            row["eastmoney_hk"] = _hk_em(ticker)
            second = row["eastmoney_hk"]
            row["cross_source_gaps_pct"] = {
                "debt": _gap((yahoo["debt"]["latest"] or {}).get("value"), second.get("debt_including_leases")),
                "cash_strict": _gap((yahoo["cash_strict"]["latest"] or {}).get("value"), second.get("cash_strict")),
                "fcf_proxy": _gap((yahoo["fcf"]["latest"] or {}).get("value"), second.get("fcf_proxy")),
            }
        if row["financial_institution"]:
            row["gates"].append("financial_institution_not_applicable")
        row["gates"].append("levered_cash_flow_proxy_not_fcff")
        if yahoo["statement_currency"] and yahoo["quote_currency"] and yahoo["statement_currency"] != yahoo["quote_currency"]:
            row["gates"].append("statement_quote_currency_mismatch_requires_timestamped_fx")
        for metric, gap in row["cross_source_gaps_pct"].items():
            if gap is None:
                row["gates"].append(f"{metric}_cross_source_not_comparable")
            elif gap > 10:
                row["gates"].append(f"{metric}_definition_or_period_gap_gt_10pct")
        row["elapsed_s"] = round(time.perf_counter() - started, 3)
        rows.append(row)
    return {
        "schema_version": "uzi.capital-bridge-shadow.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "real_data_only": True,
        "production_mutation": False,
        "rows": rows,
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# A/US/HK real capital-bridge shadow audit", "",
        f"- generated_at: `{payload['generated_at']}`",
        "- sources: Sina A-share statements, Eastmoney US/HK standardized statements, Yahoo Finance; SEC Companyfacts attempted and any network block is explicit",
        "- boundary: real observations only; shadow evidence does not enter production valuation", "",
        "| ticker | market | debt gap | strict cash gap | FCF proxy gap | gates | elapsed |",
        "|---|---|---:|---:|---:|---|---:|",
    ]
    for row in payload["rows"]:
        gaps = row["cross_source_gaps_pct"]
        lines.append(
            f"| {row['ticker']} | {row['market']} | {gaps.get('debt')} | {gaps.get('cash_strict')} | "
            f"{gaps.get('fcf_proxy')} | {', '.join(row['gates'])} | {row['elapsed_s']}s |"
        )
    lines += ["", "## Interpretation boundary", "",
              "- A provider FCFF/FCFE-per-share fields are retained as provider-defined diagnostics; they are not assumed to match CFO-capex.",
              "- Yahoo broad cash is not compared with strict cash. Deposits, short-term investments, leases, and notes remain separate components.",
              "- CFO-capex is marked levered_cash_flow_proxy. Enterprise DCF requires genuine FCFF and therefore remains fail-closed.",
              "- Financial institutions are collected for routing/contract checks only; industrial net-debt DCF is not applicable."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    payload = collect()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "capital-bridge-shadow.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "capital-bridge-shadow.md").write_text(_markdown(payload), encoding="utf-8")
    print(json.dumps({"rows": len(payload["rows"]), "output_dir": str(args.output_dir.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
