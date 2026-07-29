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


def test_common_word_tickers_require_issuer_evidence():
    from fetch_events import _news_matches_entity

    cases = [
        (
            "AI",
            "BigBear.ai Before Q2 Earnings: Buy, Sell or Hold the Stock?",
            "C3.ai, Inc.",
            False,
        ),
        (
            "AI",
            "C3.ai (AI) Gets Relief From Lawsuit Exit",
            "C3.ai, Inc.",
            True,
        ),
        (
            "ON",
            "TXN Keeps Climbing. Should You Climb On?",
            "ON Semiconductor Corporation",
            False,
        ),
        (
            "ON",
            "Micron, onsemi, Seagate stocks dive",
            "ON Semiconductor Corporation",
            True,
        ),
        (
            "IT",
            "Securden Recognized in Gartner Magic Quadrant",
            "Gartner, Inc.",
            False,
        ),
        (
            "IT",
            "Gartner (IT) Earnings Expected to Grow",
            "Gartner, Inc.",
            True,
        ),
        (
            "CAT",
            "The cat sat on a loader",
            "Caterpillar Inc.",
            False,
        ),
        (
            "CAT",
            "Caterpillar (CAT) Faces Rare Earth Squeeze",
            "Caterpillar Inc.",
            True,
        ),
    ]
    for ticker, title, company, expected in cases:
        assert _news_matches_entity(title, "", ticker, ticker, company) is expected


def test_source_bound_brands_recover_real_issuer_news():
    from fetch_events import _news_matches_entity

    cases = [
        ("C", "Citi Is Now Live With a Trade Digitization Solution", "Citigroup Inc."),
        ("GOOGL", "Google Completes Acquisition of Wiz", "Alphabet Inc."),
        ("GOOG", "Google Completes Acquisition of Wiz", "Alphabet Inc."),
        ("XYZ", "The Dark Sides Of Cash App", "Block, Inc."),
        ("GEN", "Norton Study Reveals Emerging Risks for Kids Online", "Gen Digital Inc."),
        ("GEN", "MoneyLion One Launches Premium Banking", "Gen Digital Inc."),
    ]
    for ticker, title, company in cases:
        assert _news_matches_entity(title, "", ticker, ticker, company)


def test_source_bound_aliases_do_not_enable_generic_gen_or_google_mentions():
    from fetch_events import _news_matches_entity

    assert not _news_matches_entity(
        "Gen Z investors turn cautious",
        "",
        "GEN",
        "GEN",
        "Gen Digital Inc.",
    )
    assert not _news_matches_entity(
        "Publisher cites Google Trends in retail survey",
        "",
        "META",
        "META",
        "Meta Platforms, Inc.",
    )


def test_strategy_rebrand_recovers_old_name_without_generic_word_pollution():
    from fetch_events import _news_matches_entity

    assert _news_matches_entity(
        "Michael Saylor Says Bitcoin Has Won, So Why Did MicroStrategy Stop Buying BTC?",
        "",
        "MSTR",
        "MSTR",
        "Strategy Inc.",
    )
    assert _news_matches_entity(
        "Strategy Announces Second Quarter 2026 Financial Results",
        "",
        "MSTR",
        "MSTR",
        "Strategy Inc.",
    )
    assert not _news_matches_entity(
        "Atlassian's Strategic Position in the AI Landscape",
        "",
        "MSTR",
        "MSTR",
        "Strategy Inc.",
    )
    assert not _news_matches_entity(
        "A Better Portfolio Strategy for Volatile Markets",
        "",
        "MSTR",
        "MSTR",
        "Strategy Inc.",
    )


def test_other_issuer_event_is_not_owned_by_named_partner():
    from fetch_events import _news_matches_entity

    assert not _news_matches_entity(
        "Nvidia Partner SK Hynix Misses Q2 Sales Target But Profit Surprises",
        "",
        "NVDA",
        "NVDA",
        "NVIDIA Corporation",
    )
    assert not _news_matches_entity(
        "SK hynix posts 1,200% net profit boost on AI chip boom",
        "SK hynix is a specialist supplier of high-bandwidth memory chips to US industry behemoth Nvidia.",
        "NVDA",
        "NVDA",
        "NVIDIA Corporation",
    )
    assert _news_matches_entity(
        "Nvidia Reports Record Quarterly Revenue",
        "",
        "NVDA",
        "NVDA",
        "NVIDIA Corporation",
    )
