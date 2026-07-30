from __future__ import annotations

import json
import os
from pathlib import Path

import fetch_kline
import fetch_macro
from lib import fred_source, massive_source, secure_config


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_dpapi_round_trip_is_encrypted_and_environment_wins(tmp_path, monkeypatch):
    path = tmp_path / "secure.json"
    secret = "fixture-contact@example.invalid"
    secure_config.save_secure_values(
        {"FRED_API_KEY": secret},
        path=path,
    )
    assert secret not in path.read_text(encoding="utf-8")
    assert secure_config.read_secure_values(
        ["FRED_API_KEY"],
        path=path,
    ) == {"FRED_API_KEY": secret}

    monkeypatch.setattr(secure_config, "secure_config_path", lambda: path)
    monkeypatch.setenv("FRED_API_KEY", "explicit-process-value")
    assert secure_config.load_secure_config(["FRED_API_KEY"]) == set()
    assert os.environ["FRED_API_KEY"] == "explicit-process-value"


def test_fred_preserves_dates_values_and_redacts_key(monkeypatch):
    captured = {}

    def fake_open(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return _Response(
            {
                "observations": [
                    {
                        "date": "2026-07-28",
                        "value": ".",
                        "realtime_start": "2026-07-29",
                        "realtime_end": "2026-07-29",
                    },
                    {
                        "date": "2026-07-27",
                        "value": "4.33",
                        "realtime_start": "2026-07-29",
                        "realtime_end": "2026-07-29",
                    },
                ]
            }
        )

    monkeypatch.setenv("FRED_API_KEY", "fred-test-secret")
    monkeypatch.setattr(fred_source.urllib.request, "urlopen", fake_open)
    rows = fred_source.fetch_fred_series("DFF", limit=2, as_of="2026-07-29")
    assert rows == [
        {
            "series_id": "DFF",
            "date": "2026-07-27",
            "value": 4.33,
            "realtime_start": "2026-07-29",
            "realtime_end": "2026-07-29",
        }
    ]
    assert "fred-test-secret" in captured["url"]
    redacted = str(fred_source._redacted_error(RuntimeError(captured["url"])))
    assert "fred-test-secret" not in redacted
    assert "[REDACTED]" in redacted


def test_massive_uses_bearer_auth_and_parses_eod(monkeypatch):
    captured = {}

    def fake_open(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.headers.get("Authorization")
        captured["timeout"] = timeout
        return _Response(
            {
                "results": [
                    {
                        "t": 1785211200000,
                        "o": 200.0,
                        "h": 204.0,
                        "l": 199.0,
                        "c": 203.0,
                        "v": 12345,
                        "n": 321,
                        "vw": 202.0,
                    }
                ]
            }
        )

    monkeypatch.setenv("MASSIVE_API_KEY", "massive-test-secret")
    monkeypatch.setattr(massive_source.urllib.request, "urlopen", fake_open)
    rows = massive_source.fetch_massive_eod("AAPL")
    assert len(rows) == 1
    assert rows[0]["close"] == 203.0
    assert "massive-test-secret" not in captured["url"]
    assert captured["authorization"] == "Bearer massive-test-secret"


def test_massive_comparison_never_overwrites_primary(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MASSIVE_API_KEY", "configured")
    monkeypatch.setattr(
        massive_source,
        "fetch_massive_eod",
        lambda _ticker: [{"date": "2026-07-29", "close": 101.0}],
    )
    primary = [{"Date": "2026-07-29", "Close": 100.0}]
    before = json.loads(json.dumps(primary))
    result = massive_source.compare_massive_eod("AAPL", primary)
    assert result["status"] == "same_date_close_conflict"
    assert result["overwrote_primary"] is False
    assert primary == before


def test_massive_different_dates_do_not_create_false_close_conflict(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MASSIVE_API_KEY", "configured")
    monkeypatch.setattr(
        massive_source,
        "fetch_massive_eod",
        lambda _ticker: [{"date": "2026-07-28", "close": 80.0}],
    )
    result = massive_source.compare_massive_eod(
        "HURN",
        [{"Date": "2026-07-29", "Close": 120.0}],
    )
    assert result["status"] == "massive_delayed_or_market_open"
    assert result["calendar_gap_days"] == 1
    assert result["close_diff_pct"] is None


def test_fred_shadow_does_not_fabricate_macro_sentiment(monkeypatch):
    monkeypatch.setattr(fetch_macro, "search_trusted", lambda *_a, **_k: [])
    monkeypatch.setattr(fetch_macro, "search", lambda *_a, **_k: [])
    monkeypatch.setattr(
        fetch_macro,
        "fetch_fred_macro_snapshot",
        lambda: {
            "status": "ready",
            "observations": {
                "DFF": {"latest": {"date": "2026-07-28", "value": 4.33}}
            },
            "interpretation": None,
        },
    )
    result = fetch_macro.main("Semiconductors", "U")
    assert result["data"]["rate_cycle"] is None
    assert result["data"]["fx_trend"] is None
    assert result["data"]["rate_market"] == "US"
    assert result["data"]["official_macro_observations"]["status"] == "ready"
    assert result["fallback"] is True


def test_massive_shadow_does_not_change_kline_indicators(monkeypatch):
    rows = [
        {
            "Date": f"2026-01-{day:02d}",
            "Open": float(day),
            "High": float(day + 1),
            "Low": float(day - 1),
            "Close": float(day),
            "Volume": 1000.0,
        }
        for day in range(1, 29)
    ]
    monkeypatch.setattr(fetch_kline.ds, "fetch_kline", lambda _ti: rows)
    monkeypatch.setattr(fetch_kline, "fetch_chip_distribution", lambda _ti: {})
    monkeypatch.setattr(
        massive_source,
        "compare_massive_eod",
        lambda _ticker, _rows: {
            "status": "match",
            "overwrote_primary": False,
        },
    )
    expected = fetch_kline.compute_indicators(rows)
    result = fetch_kline.main("AAPL")
    assert result["data"]["indicators"] == expected
    assert result["data"]["massive_eod_shadow"]["status"] == "match"
