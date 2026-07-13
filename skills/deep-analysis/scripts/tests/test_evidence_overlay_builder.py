from __future__ import annotations

import importlib.util
import datetime as dt
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


def test_sec_negative_event_extraction_uses_8k_item_taxonomy():
    payload = {
        "filings": {
            "recent": {
                "form": ["8-K", "8-K", "10-Q"],
                "items": ["4.02,9.01", "2.02,9.01", ""],
                "filingDate": ["2026-04-01", "2026-03-01", "2026-02-01"],
                "accessionNumber": ["0000000000-26-000001", "0000000000-26-000002", "0000000000-26-000003"],
                "primaryDocument": ["bad.htm", "earnings.htm", "10q.htm"],
            }
        }
    }
    events = evidence_overlay_builder.extract_sec_negative_events(
        payload,
        cik=1,
        ticker="TEST",
        company_name="Test Inc.",
        max_items=5,
    )
    assert len(events) == 1
    assert events[0]["severity"] == "P0"
    assert events[0]["item_code"] == "4.02"
    assert "bad.htm" in events[0]["url"]


def test_sec_negative_event_extraction_ignores_context_free_8k_items():
    payload = {
        "filings": {
            "recent": {
                "form": ["8-K"],
                "items": ["2.02,9.01"],
                "filingDate": ["2026-03-01"],
                "accessionNumber": ["0000000000-26-000002"],
                "primaryDocument": ["earnings.htm"],
            }
        }
    }
    events = evidence_overlay_builder.extract_sec_negative_events(
        payload,
        cik=1,
        ticker="TEST",
        company_name="Test Inc.",
    )
    assert events == []


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
    assert overlay["evidence"][0]["severity"] == "P0"
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
    assert overlay["display"]["target_label_zh"] == "财务字段补证据"
    assert overlay["display"]["status_label_zh"] in {"证据缺口", "证据不完整", "证据已冻结"}
    assert overlay["target"] == "missing_financials"


def test_negative_event_display_keeps_machine_enums():
    overlay = {
        "schema_version": "uzi.evidence_overlay.v1",
        "ticker": "TEST",
        "market": "US",
        "target": "negative_event",
        "status": "ready",
        "confidence": {"level": "high", "score": 85, "factors": ["required evidence is present and frozen"]},
        "evidence": [{"severity": "P1"}],
    }
    evidence_overlay_builder._attach_display_labels(overlay)
    assert overlay["target"] == "negative_event"
    assert overlay["status"] == "ready"
    assert overlay["evidence"][0]["severity"] == "P1"
    assert overlay["evidence"][0]["severity_label_zh"] == "P1 重大风险升级"
    assert overlay["display"]["status_label_zh"] == "证据已冻结"


def test_cninfo_title_taxonomy_excludes_question_replies_and_keeps_enforcement():
    assert evidence_overlay_builder.classify_cninfo_title("关于回复年报问询函的公告") is None
    assert evidence_overlay_builder.classify_cninfo_title("关于收到交易所关注函的公告") is None
    assert evidence_overlay_builder.classify_cninfo_title("关于收到行政处罚决定书的公告")["severity"] == "P1"
    assert evidence_overlay_builder.classify_cninfo_title("关于财务造假行政处罚决定书的公告")["severity"] == "P0"


def test_cninfo_fetch_uses_dynamic_org_id_and_exact_security_code():
    old_get = evidence_overlay_builder._fetch_json
    old_request = evidence_overlay_builder._fetch_json_request
    captured = {}

    def fake_get(url, *, timeout_sec, headers=None):
        assert url == evidence_overlay_builder.CNINFO_STOCK_MAP_URL
        return {"stockList": [{"code": "002038", "orgId": "gssz0002038", "zwjc": "双鹭药业"}]}

    def fake_request(url, *, timeout_sec, data=None, headers=None):
        captured.update(dict(item.split("=", 1) for item in data.decode("utf-8").split("&")))
        return {
            "announcements": [
                {
                    "secCode": "002038",
                    "announcementTitle": "关于收到行政处罚决定书的公告",
                    "announcementTime": 1777478400000,
                    "adjunctUrl": "finalpage/2026-04-30/example.PDF",
                },
                {
                    "secCode": "002039",
                    "announcementTitle": "关于收到行政处罚决定书的公告",
                    "announcementTime": 1777478400000,
                    "adjunctUrl": "finalpage/2026-04-30/wrong.PDF",
                },
            ]
        }

    try:
        evidence_overlay_builder._fetch_json = fake_get
        evidence_overlay_builder._fetch_json_request = fake_request
        events, scanned = evidence_overlay_builder.fetch_cninfo_negative_events(
            "002038.SZ", as_of=dt.date(2026, 7, 13)
        )
    finally:
        evidence_overlay_builder._fetch_json = old_get
        evidence_overlay_builder._fetch_json_request = old_request
    decoded_stock = __import__("urllib.parse", fromlist=["unquote_plus"]).unquote_plus(captured["stock"])
    assert decoded_stock == "002038,gssz0002038"
    assert scanned == 2
    assert len(events) == 1
    assert events[0]["entity_match"] == "exact"


def test_sse_action_taxonomy_does_not_promote_work_letters():
    assert evidence_overlay_builder.classify_sse_action("公开谴责")["severity"] == "P1"
    assert evidence_overlay_builder.classify_sse_action("监管关注")["severity"] == "P2"
    assert evidence_overlay_builder.classify_sse_action("监管工作函") is None


def test_szse_rows_separate_issuer_discipline_from_related_person_only():
    issuer = evidence_overlay_builder._szse_row_to_event(
        {
            "xx_gsdm": "002038",
            "xx_fwrq": "2026-04-29",
            "xx_cflb": "公开谴责",
            "xx_bt": "关于对北京双鹭药业股份有限公司及相关当事人给予纪律处分的决定",
            "ck": "<a encode-open='/UpFiles/example.pdf'>查看</a>",
        },
        code="002038",
        kind="discipline",
    )
    person = evidence_overlay_builder._szse_row_to_event(
        {
            "xx_gsdm": "002038",
            "xx_fwrq": "2026-04-29",
            "xx_cflb": "通报批评",
            "xx_bt": "关于对张三、李四给予通报批评处分的决定",
            "ck": "<a encode-open='/UpFiles/person.pdf'>查看</a>",
        },
        code="002038",
        kind="discipline",
    )
    assert issuer["severity"] == "P1" and issuer["entity_scope"] == "issuer"
    assert person["severity"] == "P2" and person["entity_scope"] == "related_person"


def test_hkex_code_match_is_exact_and_former_director_is_review_only():
    page = """
    <a href='/News/Regulatory-Announcements/2026/260709news?sc_lang=en'>
      Exchange's Disciplinary Action against Example Holdings Limited (Stock Code: 700)
    </a>
    <a href='/News/Regulatory-Announcements/2026/260708news?sc_lang=en'>
      Exchange's Disciplinary Action against Other Limited (Stock Code: 1700)
    </a>
    <a href='/News/Regulatory-Announcements/2026/260706news?sc_lang=en'>
      Exchange's Disciplinary Action against a Former Director of Example Limited (Stock Code: 171)
    </a>
    """
    events, scanned = evidence_overlay_builder.extract_hkex_negative_events(page, ticker="00700.HK")
    director_events, _ = evidence_overlay_builder.extract_hkex_negative_events(page, ticker="00171.HK")
    assert scanned == 3
    assert len(events) == 1 and events[0]["severity"] == "P1"
    assert director_events[0]["severity"] == "P2"
    assert director_events[0]["entity_scope"] == "related_person"


def test_sfc_requires_exact_stock_code_and_caps_related_person_action():
    assert evidence_overlay_builder._extract_sfc_stock_codes("(Stock code: 06161)") == {"6161"}
    assert "6161" not in evidence_overlay_builder._extract_sfc_stock_codes("(Stock code: 16161)")
    related = evidence_overlay_builder.classify_sfc_enforcement(
        "SFC seeks order against former chairman of Example Holdings Limited",
        "Example Holdings Limited (Stock code: 6161)",
    )
    issuer = evidence_overlay_builder.classify_sfc_enforcement(
        "SFC commences proceedings against Example Holdings Limited",
        "Example Holdings Limited (Stock code: 6161)",
    )
    assert related["severity"] == "P2" and related["entity_scope"] == "related_person"
    assert issuer["severity"] == "P1" and issuer["entity_scope"] == "issuer"


def test_sfc_company_tokens_must_match_target_code_context():
    title_tokens = evidence_overlay_builder._sfc_company_tokens(
        "SFC commences proceedings against Target Insurance (Holdings) Limited"
    )
    matching = evidence_overlay_builder._sfc_stock_code_contexts(
        "Target Insurance (Holdings) Limited (Stock code: 6161)", "6161"
    )
    unrelated = evidence_overlay_builder._sfc_stock_code_contexts(
        "Other Company Limited (Stock code: 6161)", "6161"
    )
    assert any(any(token in context.lower() for token in title_tokens) for context in matching)
    assert not any(any(token in context.lower() for token in title_tokens) for context in unrelated)


def test_negative_event_recency_boundary_is_inclusive_and_future_is_rejected():
    base = {
        "source": "sec_submissions",
        "url": "https://www.sec.gov/example",
        "title": "Official event",
        "severity": "P1",
        "event_type": "test",
        "official_source": True,
        "entity_match": "exact",
    }
    rows = [
        {**base, "published_at": "2024-07-13"},
        {**base, "url": "https://www.sec.gov/stale", "published_at": "2024-07-12"},
        {**base, "url": "https://www.sec.gov/future", "published_at": "2026-07-14"},
    ]
    finalized = evidence_overlay_builder._finalize_negative_events(
        rows, as_of=dt.date(2026, 7, 13), lookback_days=730, max_items=5
    )
    assert [item["url"] for item in finalized] == ["https://www.sec.gov/example"]
    assert finalized[0]["age_days"] == 730


def test_event_limit_keeps_severe_evidence_before_newer_review_only_rows():
    rows = [
        {
            "source": "sec_submissions",
            "url": "https://www.sec.gov/p0",
            "title": "Older hard risk",
            "published_at": "2025-01-01",
            "severity": "P0",
            "event_type": "hard_risk",
            "official_source": True,
            "entity_match": "exact",
        }
    ] + [
        {
            "source": "sec_submissions",
            "url": f"https://www.sec.gov/p2-{index}",
            "title": f"New review row {index}",
            "published_at": f"2026-07-{index + 1:02d}",
            "severity": "P2",
            "event_type": "review",
            "official_source": True,
            "entity_match": "exact",
        }
        for index in range(5)
    ]
    finalized = evidence_overlay_builder._finalize_negative_events(
        rows, as_of=dt.date(2026, 7, 13), lookback_days=730, max_items=2
    )
    assert finalized[0]["severity"] == "P0"
    assert any(item["url"].endswith("/p0") for item in finalized)


def test_negative_event_dedupe_keeps_stricter_severity_for_same_official_url():
    rows = [
        {
            "source": "szse_discipline",
            "url": "https://www.szse.cn/UpFiles/same.pdf",
            "title": "同一处分决定",
            "published_at": "2026-04-29",
            "severity": severity,
            "event_type": "test",
            "official_source": True,
            "entity_match": "exact",
        }
        for severity in ("P2", "P1")
    ]
    finalized = evidence_overlay_builder._finalize_negative_events(
        rows, as_of=dt.date(2026, 7, 13), lookback_days=730, max_items=5
    )
    assert len(finalized) == 1
    assert finalized[0]["severity"] == "P1"


def test_cninfo_exchange_mirror_is_merged_without_losing_provenance():
    rows = [
        {
            "source": "cninfo_company_announcement",
            "url": "https://static.cninfo.com.cn/mirror.pdf",
            "title": "关于收到深圳证券交易所纪律处分决定的公告",
            "published_at": "2026-05-05",
            "severity": "P1",
            "event_type": "cninfo_enforcement_disclosure",
            "official_source": True,
            "entity_match": "exact",
        },
        {
            "source": "szse_discipline",
            "url": "https://www.szse.cn/UpFiles/direct.pdf",
            "title": "关于对某公司给予纪律处分的决定",
            "published_at": "2026-04-29",
            "severity": "P1",
            "event_type": "szse_disciplinary_action",
            "official_source": True,
            "entity_match": "exact",
        },
    ]
    finalized = evidence_overlay_builder._finalize_negative_events(
        rows, as_of=dt.date(2026, 7, 13), lookback_days=730, max_items=5
    )
    assert len(finalized) == 1
    assert finalized[0]["source"] == "szse_discipline"
    assert finalized[0]["corroborating_sources"] == ["cninfo_company_announcement"]


def test_unofficial_cached_negative_event_cannot_become_ready_overlay():
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
                                        "title": "Company received a material fraud penalty",
                                        "url": "https://example.com/unverified",
                                        "source": "unknown",
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
            overlay = evidence_overlay_builder.build_overlay(
                "TEST", "negative_event", network=False, as_of="2026-07-13"
            )
        finally:
            evidence_overlay_builder.CACHE = old_cache
    assert overlay["status"] == "gap"
    assert overlay["evidence"][0]["official_source"] is False


def test_sec_release_rows_require_exact_registrant_identity():
    page = """
    <table><tr class="pr-list-page-row">
      <td><time datetime="2026-06-12T01:09:01Z">June 11, 2026</time></td>
      <td><div class='release-view__respondents'><a href='/files/action.pdf'>Happy City Holdings Limited</a></div>
      <span>Release No.</span><span>34-105675</span></td>
    </tr></table>
    """
    rows = evidence_overlay_builder.extract_sec_release_rows(page)
    assert rows[0]["published_at"] == "2026-06-11"
    assert evidence_overlay_builder._sec_respondent_matches_company(
        rows[0]["respondents"], "Happy City Holdings Limited"
    )
    assert not evidence_overlay_builder._sec_respondent_matches_company(
        rows[0]["respondents"], "City Holdings Limited"
    )


def test_csrc_penalty_requires_issuer_in_respondent_section():
    issuer = "中国证监会行政处罚决定书。当事人：大唐高鸿网络股份有限公司。经查，高鸿股份财务造假。"
    unrelated = "中国证监会行政处罚决定书。当事人：张三。案情涉及大唐高鸿网络股份有限公司。"
    matched = evidence_overlay_builder.classify_csrc_penalty(
        issuer, code="000851", short_name="ST高鸿"
    )
    assert matched["severity"] == "P0"
    assert evidence_overlay_builder.classify_csrc_penalty(
        unrelated, code="000851", short_name="ST高鸿"
    ) is None


def test_hkex_critical_filing_taxonomy_excludes_bare_halt_and_resumption():
    assert evidence_overlay_builder.classify_hkex_critical_filing("EXCHANGE NOTICE - TRADING HALT") is None
    assert evidence_overlay_builder.classify_hkex_critical_filing("RESUMPTION OF TRADING") is None
    assert evidence_overlay_builder.classify_hkex_critical_filing(
        "RESUMPTION GUIDANCE AND CONTINUED SUSPENSION OF TRADING"
    )["severity"] == "P1"
    assert evidence_overlay_builder.classify_hkex_critical_filing(
        "WINDING UP AND LIQUIDATION OF ISSUER"
    )["severity"] == "P0"


def test_hkex_critical_filing_extracts_exact_stock_code_only():
    page = """
    <table><tbody>
      <tr><td class="release-time">13/07/2026 08:54</td>
      <td class="stock-short-code"><span>Stock Code: </span>00841</td>
      <td><div class="headline">Announcements - [Inside Information / Suspension]</div>
      <a href="/listedco/841.pdf">DELAY IN PUBLICATION AND CONTINUED SUSPENSION</a></td></tr>
      <tr><td class="release-time">13/07/2026 08:54</td>
      <td class="stock-short-code"><span>Stock Code: </span>01841</td>
      <td><div class="headline">Announcements - [Suspension]</div>
      <a href="/listedco/1841.pdf">CONTINUED SUSPENSION</a></td></tr>
    </tbody></table>
    """
    events, scanned = evidence_overlay_builder.extract_hkex_critical_filing_events(page, ticker="00841.HK")
    assert scanned == 2
    assert len(events) == 1
    assert events[0]["severity"] == "P1"
    assert events[0]["entity_match"] == "exact"


def test_negative_event_source_plans_cover_three_independent_authority_layers():
    us = {row["source"] for row in evidence_overlay_builder.source_plan_for("US", "negative_event")}
    a_share = {row["source"] for row in evidence_overlay_builder.source_plan_for("A", "negative_event")}
    hk = {row["source"] for row in evidence_overlay_builder.source_plan_for("HK", "negative_event")}
    assert {"sec_submissions", "sec_litigation_releases", "sec_trading_suspensions"} <= us
    assert {"cninfo", "csrc_penalties"} <= a_share
    assert {"hkex_discipline", "hkex_critical_filings", "sfc_enforcement"} <= hk


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
