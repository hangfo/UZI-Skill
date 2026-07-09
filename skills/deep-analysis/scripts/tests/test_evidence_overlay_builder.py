from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
TOOL = ROOT / "tools" / "evidence_overlay_builder.py"
spec = importlib.util.spec_from_file_location("evidence_overlay_builder", TOOL)
evidence_overlay_builder = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(evidence_overlay_builder)


def test_sec_financial_fact_extraction_is_field_mapped_not_scored():
    payload = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "label": "Revenue",
                    "units": {
                        "USD": [
                            {"val": 100, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2026-02-01", "accn": "1"},
                            {"val": 90, "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2025-02-01", "accn": "0"},
                        ]
                    },
                },
                "NetIncomeLoss": {
                    "label": "Net income",
                    "units": {"USD": [{"val": 20, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2026-02-01"}]},
                },
                "Assets": {
                    "label": "Assets",
                    "units": {"USD": [{"val": 300, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2026-02-01"}]},
                },
            }
        }
    }
    fields = evidence_overlay_builder.extract_sec_financial_fields(payload, max_items=1)
    assert set(fields) >= {"revenue", "net_income", "assets"}
    assert fields["revenue"]["values"][0]["value"] == 100
    assert "investment_score" not in json.dumps(fields)


def test_missing_financials_overlay_no_network_keeps_gap_without_cache():
    old_cache = evidence_overlay_builder.CACHE
    with tempfile.TemporaryDirectory() as td:
        try:
            evidence_overlay_builder.CACHE = Path(td)
            overlay = evidence_overlay_builder.build_overlay("AAPL", "missing_financials", network=False)
        finally:
            evidence_overlay_builder.CACHE = old_cache
    assert overlay["status"] == "gap"
    assert overlay["confidence"]["level"] == "low"
    assert any("network disabled" in err["error"] for err in overlay["errors"])


def test_negative_event_overlay_does_not_infer_from_absence():
    old_cache = evidence_overlay_builder.CACHE
    with tempfile.TemporaryDirectory() as td:
        try:
            evidence_overlay_builder.CACHE = Path(td)
            overlay = evidence_overlay_builder.build_overlay("AAPL", "negative_event", network=False)
        finally:
            evidence_overlay_builder.CACHE = old_cache
    assert overlay["status"] == "gap"
    assert any("not inferred" in factor for factor in overlay["confidence"]["factors"])


def test_negative_event_cache_requires_traceable_title_and_url():
    old_cache = evidence_overlay_builder.CACHE
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cache_dir = root / "TEST"
        cache_dir.mkdir(parents=True)
        (cache_dir / "raw_data.json").write_text(
            json.dumps(
                {
                    "dimensions": {
                        "15_events": {
                            "data": {
                                "recent_news": [
                                    {
                                        "title": "SEC charges accounting fraud against executives",
                                        "url": "https://www.sec.gov/example",
                                        "source": "sec",
                                        "published_at": "2026-01-01",
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        try:
            evidence_overlay_builder.CACHE = root
            overlay = evidence_overlay_builder.build_overlay("TEST", "negative_event", network=False)
        finally:
            evidence_overlay_builder.CACHE = old_cache
    assert overlay["status"] == "ready"
    assert overlay["evidence"][0]["url"].startswith("https://www.sec.gov/")


def test_negated_negative_event_phrase_is_not_evidence():
    old_cache = evidence_overlay_builder.CACHE
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cache_dir = root / "TEST"
        cache_dir.mkdir(parents=True)
        (cache_dir / "raw_data.json").write_text(
            json.dumps(
                {
                    "dimensions": {
                        "15_events": {
                            "data": {
                                "recent_news": [
                                    {
                                        "title": "Company reports no fraud and no violation found",
                                        "url": "https://example.com/no-fraud",
                                        "source": "company",
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        try:
            evidence_overlay_builder.CACHE = root
            overlay = evidence_overlay_builder.build_overlay("TEST", "negative_event", network=False)
        finally:
            evidence_overlay_builder.CACHE = old_cache
    assert overlay["status"] == "gap"
    assert overlay["evidence"] == []


def test_overlay_schema_has_freeze_guardrails():
    overlay = evidence_overlay_builder.build_overlay("600519.SH", "missing_financials", network=False)
    assert overlay["schema_version"] == "uzi.evidence_overlay.v1"
    assert "same overlay must be reused" in " ".join(overlay["guardrails"])
    assert overlay["market"] == "A"


if __name__ == "__main__":
    import inspect
    import sys

    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not inspect.isfunction(fn):
            continue
        try:
            fn()
            print(f"PASS {name}")
            passed += 1
        except Exception as exc:
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
            failed += 1
    print(f"{passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
