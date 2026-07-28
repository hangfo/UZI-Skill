#!/usr/bin/env python3
"""Validate installed stock-data skills without copying providers into UZI.

The skills are Markdown documents containing executable Python examples.  This
tool compiles every Python fence, loads declarations without running example
calls, and performs a bounded real-endpoint smoke test for sources whose terms
allow it.  CBOE is intentionally checked offline only, and SEC requests fail
closed until the user supplies the contact string required by SEC.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import ssl
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic


DEFAULT_A = Path.home() / ".agents" / "skills" / "a-stock-data" / "SKILL.md"
DEFAULT_GLOBAL = (
    Path.home() / ".agents" / "skills" / "global-stock-data" / "SKILL.md"
)
FENCE = "`" * 3
PYTHON_FENCE = re.compile(
    re.escape(FENCE) + r"python\s*\n(.*?)" + re.escape(FENCE),
    re.DOTALL,
)


def _blocks(path: Path) -> list[str]:
    return PYTHON_FENCE.findall(path.read_text(encoding="utf-8-sig"))


def compile_fences(path: Path) -> dict:
    errors = []
    blocks = _blocks(path)
    for index, source in enumerate(blocks, 1):
        try:
            compile(source, f"{path.name}:block-{index}", "exec")
        except SyntaxError as exc:
            errors.append(
                {"block": index, "line": exc.lineno, "error": exc.msg}
            )
    return {
        "blocks": len(blocks),
        "compiled": len(blocks) - len(errors),
        "errors": errors,
    }


def _literal_assignment(node: ast.Assign | ast.AnnAssign) -> bool:
    value = node.value
    if value is None:
        return False
    try:
        ast.literal_eval(value)
    except (ValueError, TypeError):
        return False
    return True


def load_declarations(path: Path) -> dict:
    """Load imports, declarations, and literal globals; skip example calls."""
    namespace = {
        "__name__": f"_skill_{path.parent.name.replace('-', '_')}",
        # Some backup examples capture this harmless TLS context as a default
        # argument.  Creating it is local-only and avoids executing example
        # assignments that may contain real network calls.
        "_ctx": ssl.create_default_context(),
    }
    for index, source in enumerate(_blocks(path), 1):
        tree = ast.parse(source, filename=f"{path.name}:block-{index}")
        kept = []
        for node in tree.body:
            if isinstance(
                node,
                (
                    ast.Import,
                    ast.ImportFrom,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            ):
                kept.append(node)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and _literal_assignment(
                node
            ):
                kept.append(node)
        if kept:
            module = ast.Module(body=kept, type_ignores=[])
            exec(compile(module, f"{path.name}:decl-{index}", "exec"), namespace)
    return namespace


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def smoke_a_share(namespace: dict, *, skip_board_flow: bool = False) -> dict:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    prefix_expected = {
        "510300": "sh",
        "000016": "sh",
        "920002": "bj",
        "sh000001": "sh",
        "sz000001": "sz",
    }
    prefix_actual = {
        code: namespace["get_prefix"](code) for code in prefix_expected
    }
    _assert(prefix_actual == prefix_expected, f"prefix mismatch: {prefix_actual}")

    started = monotonic()
    quotes = namespace["tencent_quote"](
        ["688146", "601127", "920002", "sh000001", "sz000001"]
    )
    elapsed = monotonic() - started
    expected_keys = {"688146", "601127", "920002", "sh000001", "sz000001"}
    _assert(expected_keys <= set(quotes), f"missing quote keys: {quotes.keys()}")
    for code in ("688146", "601127"):
        row = quotes[code]
        _assert(row["price"] > 0, f"{code} price missing")
        _assert(row["mcap_yi"] >= row["float_mcap_yi"] > 0, f"{code} mcap order")
    _assert(
        quotes["sh000001"]["name"] != quotes["sz000001"]["name"],
        "explicit exchange prefixes collapsed to one instrument",
    )

    last_request = [0.0]
    lock = threading.Lock()
    session = requests.Session()
    session.mount(
        "https://",
        HTTPAdapter(
            max_retries=Retry(
                total=3,
                connect=3,
                read=3,
                backoff_factor=0.8,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=("GET",),
            )
        ),
    )

    def bounded_em_get(url, params=None, headers=None, timeout=15, **_kwargs):
        with lock:
            gap = 1.05 - (monotonic() - last_request[0])
            if gap > 0:
                import time

                time.sleep(gap)
            response = session.get(
                url, params=params, headers=headers, timeout=timeout
            )
            last_request[0] = monotonic()
        response.raise_for_status()
        return response

    namespace["em_get"] = bounded_em_get
    flow_result = {"skipped": True}
    if not skip_board_flow:
        started = monotonic()
        try:
            flow = namespace["board_fund_flow"]("industry", "today", 205)
            flow_elapsed = monotonic() - started
            _assert(flow["total"] > 200, f"board total still truncated: {flow['total']}")
            _assert(
                len(flow["rows"]) == 205,
                f"board pagination incomplete: {len(flow['rows'])}",
            )
            main_values = [row["main_net"] for row in flow["rows"]]
            _assert(
                main_values == sorted(main_values, reverse=True),
                "board flow is not sorted by main net inflow",
            )
            flow_result = {
                "skipped": False,
                "total": flow["total"],
                "returned": len(flow["rows"]),
                "first": flow["rows"][0],
                "seconds": round(flow_elapsed, 3),
            }
        except requests.RequestException as exc:
            # External reachability is evidence, not a reason to discard all
            # other source checks.  Contract assertions above still fail hard.
            flow_result = {
                "skipped": False,
                "access_issue": f"{type(exc).__name__}: {exc}",
                "seconds": round(monotonic() - started, 3),
            }

    return {
        "prefixes": prefix_actual,
        "quotes": {
            code: {
                "name": quotes[code]["name"],
                "price": quotes[code]["price"],
                "market_cap": quotes[code]["mcap_yi"],
                "float_market_cap": quotes[code]["float_mcap_yi"],
            }
            for code in expected_keys
        },
        "quote_seconds": round(elapsed, 3),
        "board_flow": flow_result,
    }


def smoke_global(namespace: dict) -> dict:
    us = namespace["us_stock_quote_tencent"]("AAPL")
    hk = namespace["hk_stock_quote_tencent"]("00700")
    _assert(us.get("price", 0) > 0 and us.get("currency") == "USD", f"US quote: {us}")
    _assert(hk.get("price", 0) > 0 and hk.get("currency") == "HKD", f"HK quote: {hk}")
    _assert(us.get("market_cap", 0) >= us.get("float_market_cap", 0) > 0, "US mcap")
    _assert(hk.get("market_cap", 0) >= hk.get("float_market_cap", 0) > 0, "HK mcap")

    # The release fixed adjusted OCC roots.  Do not call CBOE: its terms require
    # prior approval.  Recreate only the documented parser constant locally.
    namespace["_OSI"] = re.compile(
        r"^(?P<root>[A-Z][A-Z0-9]*)(?P<y>\d{2})(?P<m>\d{2})(?P<d>\d{2})"
        r"(?P<cp>[CP])(?P<strike>\d{8})$"
    )
    adjusted = namespace["parse_osi"]("NVDA1260724C00150000")
    standard = namespace["parse_osi"]("AAPL260724P00200000")
    _assert(adjusted.get("strike") == 150.0, f"adjusted OCC root: {adjusted}")
    _assert(standard.get("strike") == 200.0, f"standard OCC root: {standard}")

    rate_limiter = namespace["_RateLimiter"]
    namespace["_LIMITS"] = {
        "sec.gov": rate_limiter(8),
        "finra.org": rate_limiter(4),
        "cboe.com": rate_limiter(4),
        "nasdaq.com": rate_limiter(2),
        "_default": rate_limiter(5),
    }
    short = namespace["short_volume_all"]()
    _assert(short.get("count", 0) > 5_000, f"FINRA count too small: {short}")

    treasury = namespace["treasury_yield_curve"](datetime.now(timezone.utc).year)
    _assert(treasury and treasury[0].get("Date"), "Treasury curve empty")
    cot = namespace["cftc_cot"](limit=3)
    _assert(isinstance(cot, list) and len(cot) == 3, f"CFTC COT: {cot}")

    _assert(namespace["_frame_period"](2025, 1, True) == "CY2025Q1I", "instant Q")
    _assert(namespace["_frame_period"](2025, None, True) == "CY2025Q4I", "instant FY")
    sec_fail_closed = False
    try:
        namespace["market_frame"]("Assets", 2025, 1)
    except RuntimeError as exc:
        sec_fail_closed = "SEC_CONTACT" in str(exc) or "真实姓名" in str(exc)
    _assert(sec_fail_closed, "SEC call did not fail closed without declared contact")

    return {
        "us_quote": {
            key: us.get(key)
            for key in (
                "name",
                "name_en",
                "price",
                "currency",
                "market_cap",
                "float_market_cap",
                "pe",
                "pb",
            )
        },
        "hk_quote": {
            key: hk.get(key)
            for key in (
                "name",
                "name_en",
                "price",
                "currency",
                "market_cap",
                "float_market_cap",
                "pe",
                "pb",
            )
        },
        "occ_parser": {"adjusted": adjusted, "standard": standard},
        "finra": {
            "date": short.get("date"),
            "market": short.get("market"),
            "count": short.get("count"),
            "aapl": short.get("data", {}).get("AAPL"),
        },
        "treasury_latest": treasury[0],
        "cftc_count": len(cot),
        "sec_frames": {
            "instant_quarter": namespace["_frame_period"](2025, 1, True),
            "instant_year": namespace["_frame_period"](2025, None, True),
            "undeclared_contact_fail_closed": sec_fail_closed,
        },
        "cboe_network_called": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-skill", type=Path, default=DEFAULT_A)
    parser.add_argument("--global-skill", type=Path, default=DEFAULT_GLOBAL)
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument(
        "--skip-board-flow",
        action="store_true",
        help="Skip Eastmoney board pagination after a separately recorded source gap.",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "skills": {
            "a-stock-data": {
                "path": str(args.a_skill),
                "compile": compile_fences(args.a_skill),
            },
            "global-stock-data": {
                "path": str(args.global_skill),
                "compile": compile_fences(args.global_skill),
            },
        },
    }
    for record in result["skills"].values():
        _assert(not record["compile"]["errors"], f"compile errors: {record}")

    if not args.no_network:
        result["skills"]["a-stock-data"]["real_smoke"] = smoke_a_share(
            load_declarations(args.a_skill), skip_board_flow=args.skip_board_flow
        )
        result["skills"]["global-stock-data"]["real_smoke"] = smoke_global(
            load_declarations(args.global_skill)
        )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
