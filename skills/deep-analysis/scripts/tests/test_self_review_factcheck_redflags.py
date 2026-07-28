import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def _ctx(ticker, name, industry, commentary):
    return {
        "ticker": ticker,
        "market": "U",
        "dims": {
            "0_basic": {
                "data": {
                    "name": name,
                    "industry": industry,
                    "main_business": "",
                }
            }
        },
        "syn": {
            "name": name,
            "dim_commentary": {"0_basic": commentary},
        },
        "ag": {},
    }


def test_apple_itself_is_not_misread_as_apple_supply_chain_claim():
    from lib.self_review import check_factcheck_redflags

    issues = check_factcheck_redflags(
        _ctx(
            "AAPL",
            "Apple Inc.",
            "Consumer Electronics",
            "基础信息：Apple Inc.（AAPL），Consumer Electronics 行业。",
        )
    )

    assert not issues


def test_non_apple_supplier_claim_still_requires_business_evidence():
    from lib.self_review import check_factcheck_redflags

    issues = check_factcheck_redflags(
        _ctx(
            "FAKE",
            "Example Inc.",
            "Consumer Electronics",
            "公司进入 Apple 产业链，订单弹性很大。",
        )
    )

    assert len(issues) == 1
    assert "苹果产业链" in issues[0].issue


def test_non_apple_supplier_with_optics_evidence_is_allowed():
    from lib.self_review import check_factcheck_redflags

    issues = check_factcheck_redflags(
        _ctx(
            "LENS",
            "Lens Supplier",
            "光学镜头精密制造",
            "公司进入 Apple 产业链，订单弹性很大。",
        )
    )

    assert not issues


def test_tesla_itself_is_not_misread_as_tesla_supply_chain_claim():
    from lib.self_review import check_factcheck_redflags

    issues = check_factcheck_redflags(
        _ctx(
            "TSLA",
            "Tesla, Inc.",
            "Auto Manufacturers",
            "Tesla 受益于电动车需求。",
        )
    )

    assert not issues


def test_comparative_tesla_mention_is_not_a_supply_chain_claim():
    from lib.self_review import check_factcheck_redflags

    issues = check_factcheck_redflags(
        _ctx(
            "MU",
            "Micron Technology, Inc.",
            "Semiconductors",
            "Micron shares fell while Tesla and Apple moved higher.",
        )
    )

    assert not issues


def test_tesla_supplier_claim_still_requires_business_evidence():
    from lib.self_review import check_factcheck_redflags

    issues = check_factcheck_redflags(
        _ctx(
            "FAKE",
            "Example Inc.",
            "Software",
            "公司已经进入 Tesla 供应链并获得订单。",
        )
    )

    assert len(issues) == 1
    assert "特斯拉供应链" in issues[0].issue
