"""BSE quote routing regression tests.

The market router already recognized 920xxx as Beijing listings, but the two
direct quote transports used independent prefix heuristics.  Keep all three
paths on the same canonical rule.
"""

from lib.market_router import a_share_transport_prefix, parse_ticker


def test_bse_920_uses_bj_transport_prefix():
    ticker = parse_ticker("920002")

    assert ticker.full == "920002.BJ"
    assert a_share_transport_prefix(ticker.code) == "bj"


def test_exchange_prefix_boundaries_remain_distinct():
    expected = {
        "920002": "bj",
        "830799": "bj",
        "688146": "sh",
        "510300": "sh",
        "000001": "sz",
        "159915": "sz",
    }

    assert {code: a_share_transport_prefix(code) for code in expected} == expected
