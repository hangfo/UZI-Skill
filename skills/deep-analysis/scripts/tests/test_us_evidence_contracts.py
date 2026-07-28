import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def test_macro_missing_search_evidence_stays_missing(monkeypatch):
    import fetch_macro

    monkeypatch.setattr(fetch_macro, "search", lambda *args, **kwargs: [])
    monkeypatch.setattr(fetch_macro, "search_trusted", lambda *args, **kwargs: [])

    result = fetch_macro.main("Semiconductors", "U")

    assert result["fallback"] is True
    assert result["data"]["rate_market"] == "US"
    assert result["data"]["rate_cycle"] is None
    assert result["data"]["fx_trend"] is None
    assert result["data"]["industry_macro_impact"] is None


def test_macro_routes_rate_cycle_by_market(monkeypatch):
    import fetch_macro

    def trusted(query, **kwargs):
        if "美联储" in query:
            return [{"body": "美联储降息，政策宽松，市场回暖"}]
        if "中国 利率" in query:
            return [{"body": "中国加息，政策紧缩，经济下行"}]
        return []

    monkeypatch.setattr(fetch_macro, "search", lambda *args, **kwargs: [])
    monkeypatch.setattr(fetch_macro, "search_trusted", trusted)

    us = fetch_macro.main("Semiconductors", "U")["data"]
    cn = fetch_macro.main("半导体", "A")["data"]

    assert us["rate_market"] == "US"
    assert us["rate_cycle"].startswith("利好")
    assert "美联储利率" in us["rate_cycle"]
    assert cn["rate_market"] == "CN"
    assert cn["rate_cycle"].startswith("利空")
    assert "中国货币政策" in cn["rate_cycle"]


def test_pipeline_macro_adapter_routes_string_ticker_as_us():
    from lib.pipeline.fetchers.registry import FETCHER_REGISTRY

    args = FETCHER_REGISTRY["3_macro"]._args_fn(
        "MU",
        {"0_basic": {"data": {"industry": "Semiconductors"}}},
    )

    assert args == ("Semiconductors", "U")


def test_short_ticker_does_not_match_inside_unrelated_words():
    from fetch_events import _news_matches_entity

    assert not _news_matches_entity(
        "Elon Musk's Tesla and SpaceX outline a new strategy",
        "Technology shares were active.",
        "MU",
        "MU",
        "Micron Technology, Inc.",
    )
    assert _news_matches_entity(
        "Micron raises memory-chip outlook",
        "",
        "MU",
        "MU",
        "Micron Technology, Inc.",
    )
    assert _news_matches_entity(
        "Why MU shares moved today",
        "",
        "MU",
        "MU",
        "Micron Technology, Inc.",
    )
