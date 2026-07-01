import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def test_a_share_field_gate_normalizes_market_cap_and_change_pct(monkeypatch):
    import lib.data_sources as ds
    from lib.market_router import parse_ticker

    monkeypatch.setattr(ds, "_fetch_price_tencent_qt", lambda *_args: {})

    out = {
        "code": "600519.SH",
        "name": "贵州茅台",
        "industry": "白酒",
        "price": 1185.49,
        "prev_close": 1194.96,
        "change_pct": 396.08,
        "pe_ttm": 13.6,
        "pb": 5.47,
        "market_cap": 1_481_959_237_169.49,
        "listed_date": "2001-08-27",
    }

    fixed = ds._ensure_a_share_basic_fields(out, parse_ticker("600519"))

    assert fixed["market_cap_raw"] == 1_481_959_237_169.49
    assert fixed["market_cap"] == "14819.6亿"
    assert fixed["change_pct"] == -0.79


def test_a_share_field_gate_preserves_valid_change_pct(monkeypatch):
    import lib.data_sources as ds
    from lib.market_router import parse_ticker

    monkeypatch.setattr(ds, "_fetch_price_tencent_qt", lambda *_args: {})
    out = {
        "code": "300750.SZ",
        "name": "宁德时代",
        "industry": "电池",
        "price": 393.01,
        "prev_close": 392.36,
        "change_pct": 0.17,
        "pe_ttm": 21.92,
        "pb": 5.09,
        "market_cap": "18183.1亿",
        "listed_date": "2018-06-11",
    }

    fixed = ds._ensure_a_share_basic_fields(out, parse_ticker("300750"))

    assert abs(fixed["market_cap_raw"] - 1_818_310_000_000.0) < 1
    assert fixed["market_cap"] == "18183.1亿"
    assert fixed["change_pct"] == 0.17


def test_hk_yahoo_symbol_keeps_four_digits():
    import lib.data_sources as ds

    assert ds._hk_yahoo_symbol("00700") == "0700.HK"
    assert ds._hk_yahoo_symbol("09988") == "9988.HK"
    assert ds._hk_yahoo_symbol("00005") == "0005.HK"


def test_hk_market_cap_normalizer_handles_legacy_spot_shape():
    import lib.data_sources as ds

    out = {"market_cap": 3_326_651_981_026.16}
    ds._normalize_market_cap_fields(out)

    assert out["market_cap_raw"] == 3_326_651_981_026.16
    assert out["market_cap"] == "33266.5亿"


def test_kline_filters_nan_rows_before_stats():
    from fetch_kline import _extract_for_viz, compute_indicators

    rows = [
        {"日期": "2026-01-02", "开盘": 100, "收盘": 100, "最高": 101, "最低": 99, "成交量": 1},
        {"日期": "2026-01-05", "开盘": float("nan"), "收盘": float("nan"), "最高": float("nan"), "最低": float("nan"), "成交量": 0},
        {"日期": "2026-01-06", "开盘": 110, "收盘": 120, "最高": 121, "最低": 109, "成交量": 2},
    ]

    viz = _extract_for_viz(rows)
    ind = compute_indicators(rows)

    assert viz["kline_stats"]["ytd_return"] == "+20.0%"
    assert viz["close_60d"] == [100.0, 120.0]
    assert ind["last_close"] == 120.0


def test_lite_profile_sets_fund_limit(monkeypatch):
    from lib.analysis_profile import apply_profile_to_env, get_profile

    monkeypatch.delenv("UZI_FUND_LIMIT", raising=False)
    monkeypatch.delenv("UZI_CONTEST_LIMIT", raising=False)
    monkeypatch.delenv("UZI_CONTEST_HEAVY", raising=False)
    apply_profile_to_env(get_profile("lite"))
    assert __import__("os").environ["UZI_FUND_LIMIT"] == "5"
    assert __import__("os").environ["UZI_CONTEST_LIMIT"] == "20"
    assert __import__("os").environ["UZI_CONTEST_HEAVY"] == "0"

    monkeypatch.delenv("UZI_CONTEST_LIMIT", raising=False)
    monkeypatch.delenv("UZI_CONTEST_HEAVY", raising=False)
    apply_profile_to_env(get_profile("medium"))
    assert __import__("os").environ["UZI_FUND_LIMIT"] == "100"
    assert __import__("os").environ["UZI_CONTEST_LIMIT"] == "80"
    assert __import__("os").environ["UZI_CONTEST_HEAVY"] == "0"

    monkeypatch.delenv("UZI_CONTEST_LIMIT", raising=False)
    monkeypatch.delenv("UZI_CONTEST_HEAVY", raising=False)
    apply_profile_to_env(get_profile("deep"))
    assert __import__("os").environ["UZI_FUND_LIMIT"] == "all"
    assert __import__("os").environ["UZI_CONTEST_LIMIT"] == "all"
    assert __import__("os").environ["UZI_CONTEST_HEAVY"] == "1"


def test_global_listing_suffixes_route_without_breaking_us_classes():
    from lib.market_router import parse_ticker

    assert parse_ticker("SIVE.ST").market == "G"
    assert parse_ticker("7203.T").market == "G"
    assert parse_ticker("2330.TW").market == "G"
    assert parse_ticker("2330.TWO").market == "G"
    assert parse_ticker("BRK.B").market == "U"
    assert parse_ticker("600519.SH").market == "A"
    assert parse_ticker("00700.HK").market == "H"


def test_fund_holders_env_limit_caps_lite_rows(monkeypatch):
    import fetch_fund_holders as ffh

    holders = [
        {"基金名称": f"主动基金{i}", "基金代码": f"00{i:04d}", "占市值比例": str(10 - i)}
        for i in range(12)
    ]
    monkeypatch.setenv("UZI_FUND_LIMIT", "5")
    monkeypatch.setenv("UZI_FUND_STATS_TOP", "0")
    monkeypatch.setattr(ffh, "fetch_holding_funds", lambda _code: holders)
    monkeypatch.setattr(ffh, "cached", lambda _ticker, _key, fn, ttl=None: fn())

    out = ffh.main("600519")
    data = out["data"]

    assert data["total_funds_holding"] == 12
    assert data["active_funds_count"] == 12
    assert len(data["fund_managers"]) == 5
    assert data["lite_count"] == 5


def test_pipeline_collect_respects_lite_profile(monkeypatch):
    import importlib

    collect_mod = importlib.import_module("lib.pipeline.collect")

    monkeypatch.setenv("UZI_DEPTH", "lite")
    calls = []

    class FakeResult:
        top_level_fields = {}
        quality = type("Q", (), {"value": "full"})()

        def __init__(self, dim):
            self.dim = dim

        def to_dict(self):
            return {"data": {"ok": True}, "_pipeline": {"quality": "full"}}

    class FakeFetcher:
        _legacy_module = "fake"

        def __init__(self, dim):
            self.dim = dim

        def fetch(self, _ticker):
            calls.append(self.dim)
            return FakeResult(self.dim)

    def fake_get_fetcher(dim):
        return FakeFetcher(dim)

    monkeypatch.setattr(collect_mod, "get_fetcher", fake_get_fetcher)
    out = collect_mod.collect("600519", raw_previous={}, max_workers=1)

    assert set(calls) == {"0_basic", "1_financials", "2_kline", "10_valuation", "11_governance", "15_events", "16_lhb"}
    assert "6_fund_holders" not in out
    assert "19_contests" not in out
