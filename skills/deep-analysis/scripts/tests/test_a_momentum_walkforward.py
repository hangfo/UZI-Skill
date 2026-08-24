from __future__ import annotations

import a_momentum_walkforward as amw


def test_normalise_accepts_cn_rows_and_deduplicates_dates():
    rows = amw._normalise([
        {"日期": "2026-08-22", "开盘": 10, "最高": 12, "最低": 9, "收盘": 11, "成交量": 100},
        {"date": "2026-08-21", "open": 8, "high": 9, "low": 7, "close": 8.5, "volume": 80},
        {"日期": "2026-08-22", "开盘": 11, "最高": 13, "最低": 10, "收盘": 12, "成交量": 120},
        {"日期": "bad", "收盘": 0},
    ])

    assert [row["Date"] for row in rows] == ["2026-08-21", "2026-08-22"]
    assert rows[-1]["Close"] == 12.0
    assert rows[-1]["Volume"] == 120.0


def test_fetch_history_keeps_complete_primary(monkeypatch):
    primary = [{"日期": f"2026-01-{day:02d}", "收盘": day} for day in range(1, 6)]
    monkeypatch.setattr(amw, "fetch_kline", lambda *args, **kwargs: primary)

    rows, source = amw._fetch_history("300024.SZ", "20260101", required_rows=5)

    assert len(rows) == 5
    assert source == "UZI A-share source chain"


def test_fetch_history_replaces_shallow_primary(monkeypatch):
    primary = [{"日期": "2026-01-01", "收盘": 1}]
    fallback = [
        {"date": f"2026-01-{day:02d}", "close": day}
        for day in range(1, 6)
    ]

    class Provider:
        def fetch_kline_a(self, ticker, start):
            assert ticker == "300024.SZ"
            assert start == "2026-01-01"
            return fallback

    monkeypatch.setattr(amw, "fetch_kline", lambda *args, **kwargs: primary)
    monkeypatch.setattr(amw, "_BaostockProvider", Provider)

    rows, source = amw._fetch_history("300024.SZ", "20260101", required_rows=5)

    assert len(rows) == 5
    assert source.startswith("BaoStock qfq fallback")
