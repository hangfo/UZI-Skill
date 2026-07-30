"""Validate configured official sources without ever printing secret values."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib.secure_config import configured_keys, load_secure_config  # noqa: E402


def _safe_error(exc: Exception) -> str:
    text = str(exc)
    for name in ("FRED_API_KEY", "MASSIVE_API_KEY", "UZI_SEC_USER_AGENT"):
        value = os.environ.get(name)
        if value:
            text = text.replace(value, "[REDACTED]")
    return f"{type(exc).__name__}: {text[:180]}"


def validate(*, network: bool) -> dict:
    configured = configured_keys()
    load_secure_config()
    result = {
        "network": bool(network),
        "configured": {key: key in configured for key in sorted(configured | {
            "UZI_SEC_USER_AGENT", "FRED_API_KEY", "MASSIVE_API_KEY"
        })},
        "sources": {},
    }

    try:
        spec = importlib.util.spec_from_file_location(
            "evidence_overlay_builder",
            ROOT / "tools" / "evidence_overlay_builder.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        module._declared_sec_user_agent()
        if network:
            payload = module._fetch_json_request(
                module.SEC_TICKERS_URL,
                timeout_sec=12,
            )
            ok = isinstance(payload, dict) and bool(payload)
        else:
            ok = True
        result["sources"]["sec"] = {"ok": ok, "mode": "live" if network else "config"}
    except Exception as exc:
        result["sources"]["sec"] = {"ok": False, "error": _safe_error(exc)}

    try:
        from lib.fred_source import fetch_fred_series

        if not os.environ.get("FRED_API_KEY"):
            raise RuntimeError("FRED_API_KEY is not configured")
        rows = fetch_fred_series("DFF", limit=2, network=network)
        result["sources"]["fred"] = {
            "ok": bool(rows) if network else True,
            "mode": "live" if network else "config",
            "observations": len(rows) if network else None,
        }
    except Exception as exc:
        result["sources"]["fred"] = {"ok": False, "error": _safe_error(exc)}

    try:
        from lib.massive_source import fetch_massive_eod

        if not os.environ.get("MASSIVE_API_KEY"):
            raise RuntimeError("MASSIVE_API_KEY is not configured")
        rows = fetch_massive_eod("AAPL", lookback_days=10, network=network)
        result["sources"]["massive"] = {
            "ok": bool(rows) if network else True,
            "mode": "live" if network else "config",
            "bars": len(rows) if network else None,
        }
    except Exception as exc:
        result["sources"]["massive"] = {"ok": False, "error": _safe_error(exc)}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = validate(network=args.network)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for source, status in result["sources"].items():
            print(f"{source}: {'ok' if status.get('ok') else 'unavailable'}")
    return 0 if all(item.get("ok") for item in result["sources"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
