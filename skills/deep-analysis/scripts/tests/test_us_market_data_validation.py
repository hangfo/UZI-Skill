import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def test_fetch_basic_us_normalizes_market_cap_and_fast_info(monkeypatch):
    import lib.data_sources as ds
    from lib.market_router import parse_ticker

    class FakeTicker:
        def __init__(self, code):
            assert code == "AAPL"
            self.info = {
                "longName": "Apple Inc.",
                "industry": "Consumer Electronics",
                "marketCap": 3_100_000_000_000,
                "currentPrice": 0,
                "regularMarketPrice": None,
                "regularMarketPreviousClose": 190,
                "trailingPE": 28.5,
                "priceToBook": 42.0,
            }
            self.fast_info = {"lastPrice": 200}

    class FakeYF:
        Ticker = FakeTicker

    monkeypatch.setattr(ds, "yf", FakeYF)
    monkeypatch.setattr(ds, "_fetch_price_tencent_qt", lambda *_args: {})

    out = ds._fetch_basic_us(parse_ticker("AAPL"))

    assert out["price"] == 200
    assert out["market_cap_raw"] == 3_100_000_000_000
    assert out["market_cap"] == "31000.0亿"
    assert round(out["change_pct"], 2) == 5.26
    assert "yfinance.fast_info" in out["_fallback_snap"]


def test_fetch_basic_us_derives_market_cap_when_info_missing(monkeypatch):
    import lib.data_sources as ds
    from lib.market_router import parse_ticker

    class FakeTicker:
        info = {
            "shortName": "Example",
            "regularMarketPrice": None,
            "sharesOutstanding": 1_000_000_000,
        }
        fast_info = {}

        def __init__(self, _code):
            pass

    class FakeYF:
        Ticker = FakeTicker

    monkeypatch.setattr(ds, "yf", FakeYF)
    monkeypatch.setattr(ds, "_fetch_price_tencent_qt", lambda *_args: {"price": 12.5})

    out = ds._fetch_basic_us(parse_ticker("EXM"))

    assert out["price"] == 12.5
    assert out["market_cap_raw"] == 12_500_000_000
    assert out["market_cap"] == "125.0亿"
    assert "tencent_qt" in out["_fallback_snap"]


def test_extract_for_viz_ytd_uses_calendar_year_first_trade():
    from fetch_kline import _extract_for_viz

    rows = [
        {"日期": "2025-12-30", "开盘": 80, "收盘": 80, "最高": 81, "最低": 79},
        {"日期": "2025-12-31", "开盘": 90, "收盘": 90, "最高": 91, "最低": 89},
        {"日期": "2026-01-02", "开盘": 100, "收盘": 100, "最高": 101, "最低": 99},
        {"日期": "2026-01-05", "开盘": 110, "收盘": 120, "最高": 121, "最低": 109},
    ]

    out = _extract_for_viz(rows)

    assert out["kline_stats"]["ytd_return"] == "+20.0%"
