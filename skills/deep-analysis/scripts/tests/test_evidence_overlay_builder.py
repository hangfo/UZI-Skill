from __future__ import annotations

import importlib.util
import datetime as dt
import gzip
import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
TOOL = ROOT / "tools" / "evidence_overlay_builder.py"
spec = importlib.util.spec_from_file_location("evidence_overlay_builder", TOOL)
evidence_overlay_builder = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(evidence_overlay_builder)


def test_sec_network_requires_truthful_declared_identity_before_urlopen():
    old_value = os.environ.pop("UZI_SEC_USER_AGENT", None)
    called = False
    old_urlopen = evidence_overlay_builder.urllib.request.urlopen

    def forbidden_urlopen(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("urlopen must not be reached without SEC identity")

    evidence_overlay_builder.urllib.request.urlopen = forbidden_urlopen
    try:
        try:
            evidence_overlay_builder._fetch_json_request(
                "https://data.sec.gov/submissions/CIK0000320193.json",
                timeout_sec=1,
            )
        except RuntimeError as exc:
            assert "truthful" in str(exc)
        else:
            raise AssertionError("missing SEC identity must fail closed")
    finally:
        evidence_overlay_builder.urllib.request.urlopen = old_urlopen
        if old_value is not None:
            os.environ["UZI_SEC_USER_AGENT"] = old_value
    assert not called


def test_sec_network_rejects_placeholder_identity():
    old_value = os.environ.get("UZI_SEC_USER_AGENT")
    try:
        for value in (
            "UZI-Skill contact@example.com",
            "Example your-email@example.com",
            "Sample AdminContact@samplecompanydomain.com",
            "Your Real Name UZI-Skill/3.2 your.real.email@example.com",
        ):
            os.environ["UZI_SEC_USER_AGENT"] = value
            try:
                evidence_overlay_builder._declared_sec_user_agent()
            except RuntimeError:
                pass
            else:
                raise AssertionError(f"placeholder identity was accepted: {value}")
    finally:
        if old_value is None:
            os.environ.pop("UZI_SEC_USER_AGENT", None)
        else:
            os.environ["UZI_SEC_USER_AGENT"] = old_value


def test_sec_identity_is_scoped_to_sec_hosts_only():
    old_value = os.environ.get("UZI_SEC_USER_AGENT")
    declared = "Real Researcher UZI-Skill/3.2 researcher@real-domain.test"
    try:
        os.environ["UZI_SEC_USER_AGENT"] = declared
        sec_headers = evidence_overlay_builder._request_headers(
            "https://data.sec.gov/submissions/CIK0000320193.json",
            accept="application/json",
            overrides={"User-Agent": "Mozilla/5.0"},
        )
        ir_headers = evidence_overlay_builder._request_headers(
            "https://investor.example.org/news",
            accept="text/html",
        )
    finally:
        if old_value is None:
            os.environ.pop("UZI_SEC_USER_AGENT", None)
        else:
            os.environ["UZI_SEC_USER_AGENT"] = old_value
    assert sec_headers["User-Agent"] == declared
    assert sec_headers["Accept-Encoding"] == "gzip, deflate"
    assert ir_headers["User-Agent"] == evidence_overlay_builder.DEFAULT_HTTP_USER_AGENT
    assert declared not in json.dumps(ir_headers)


def test_sec_rate_limit_is_host_scoped_and_leaves_headroom():
    assert evidence_overlay_builder.SEC_REQUESTS_PER_SECOND == 8.0
    assert evidence_overlay_builder.SEC_REQUESTS_PER_SECOND < 10.0
    assert evidence_overlay_builder._is_sec_url("https://www.sec.gov/Archives/test")
    assert evidence_overlay_builder._is_sec_url("https://data.sec.gov/api/xbrl/test")
    assert not evidence_overlay_builder._is_sec_url("https://notsec.gov.example/test")
    assert not evidence_overlay_builder._is_sec_url("https://investor.example.org/test")


def test_sec_gzip_response_is_decoded_for_urllib_transport():
    class Headers(dict):
        def get_content_charset(self):
            return "utf-8"

    class Response:
        headers = Headers({"Content-Encoding": "gzip"})

        def read(self):
            return gzip.compress('{"name":"APPLE INC"}'.encode("utf-8"))

    decoded = evidence_overlay_builder._read_response_bytes(Response())
    assert json.loads(decoded.decode("utf-8"))["name"] == "APPLE INC"


def test_evidence_overlay_cli_network_is_explicit_opt_in():
    assert not evidence_overlay_builder.parse_args(
        ["--ticker", "AAPL", "--target", "missing_financials"]
    ).allow_network
    assert evidence_overlay_builder.parse_args(
        [
            "--ticker",
            "AAPL",
            "--target",
            "missing_financials",
            "--allow-network",
        ]
    ).allow_network


def test_programmatic_overlay_network_is_off_by_default():
    old_cache = evidence_overlay_builder.CACHE
    with tempfile.TemporaryDirectory() as td:
        try:
            evidence_overlay_builder.CACHE = Path(td)
            overlay = evidence_overlay_builder.build_overlay(
                "AAPL",
                "missing_financials",
            )
        finally:
            evidence_overlay_builder.CACHE = old_cache
    assert overlay["status"] == "gap"
    assert any("network disabled" in row["error"] for row in overlay["errors"])


def test_evidence_overlay_has_no_cboe_network_source_without_license():
    plans = []
    for market in ("US", "A", "HK"):
        for target in evidence_overlay_builder.SUPPORTED_TARGETS:
            plans.extend(evidence_overlay_builder.source_plan_for(market, target))
    assert "cboe" not in json.dumps(plans).lower()
    assert all("cboe" not in suffix for suffix in evidence_overlay_builder.OFFICIAL_EVENT_HOST_SUFFIXES)


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


def test_real_smci_sec_excerpts_classify_active_then_closed():
    active_excerpt = """
    The Company received a notification letter from Nasdaq indicating that the
    Company is not in compliance with Nasdaq Listing Rule 5250(c)(1), as a
    result of the Company's delay in filing its Annual Report on Form 10-K.
    """
    closed_excerpt = """
    The Company received a notification letter from Nasdaq indicating that the
    Company now complies with Nasdaq listing rule 5250(c)(1), which requires
    timely filing of reports with the SEC, and the matter is now closed.
    """
    exception_excerpt = """
    Nasdaq has granted the Company's request for an exception to Nasdaq's
    Listing Rule 5250(c)(1) through February 25, 2025. The exception gives the
    Company until February 25, 2025 to file its required periodic reports.
    """

    active = evidence_overlay_builder.classify_sec_listing_lifecycle(active_excerpt)
    closed = evidence_overlay_builder.classify_sec_listing_lifecycle(closed_excerpt)
    exception = evidence_overlay_builder.classify_sec_listing_lifecycle(exception_excerpt)

    assert active["phase"] == "active"
    assert closed["phase"] == "resolved"
    assert exception["phase"] == "active"
    assert exception["resolution_signal"] == "temporary_exception_pending_filings"
    assert active["lifecycle_key"] == closed["lifecycle_key"]


def test_sec_resolution_links_only_earlier_same_rule_event():
    active = {
        "source": "sec_submissions",
        "url": "https://www.sec.gov/Archives/active.htm",
        "title": "SMCI Item 3.01 active filing",
        "published_at": "2024-09-20",
        "severity": "P1",
        "source_record_id": "active",
        "canonical_event_id": "sec_submissions:active",
    }
    unrelated = {
        "source": "sec_submissions",
        "url": "https://www.sec.gov/Archives/unrelated.htm",
        "title": "Issuer auditor change",
        "published_at": "2024-11-18",
        "severity": "P1",
        "source_record_id": "auditor",
        "canonical_event_id": "sec_submissions:auditor",
    }
    closed = {
        "source": "sec_submissions",
        "url": "https://www.sec.gov/Archives/closed.htm",
        "title": "SMCI Item 3.01 compliance filing",
        "published_at": "2025-02-26",
        "severity": "P1",
        "source_record_id": "closed",
        "canonical_event_id": "sec_submissions:closed",
    }
    topic = "nasdaq_periodic_reporting_rule_5250_c_1"
    key = "sec:nasdaq:5250(c)(1):periodic_reporting"
    classifications = {
        "active": {"phase": "active", "resolution_status": "unknown", "lifecycle_topic": topic, "lifecycle_key": key},
        "closed": {"phase": "resolved", "resolution_status": "closed", "lifecycle_topic": topic, "lifecycle_key": key},
    }

    rows, links = evidence_overlay_builder.apply_sec_listing_lifecycle(
        [active, unrelated, closed], classifications
    )

    assert {row["source_record_id"] for row in rows} == {"active", "auditor"}
    linked = next(row for row in rows if row["source_record_id"] == "active")
    untouched = next(row for row in rows if row["source_record_id"] == "auditor")
    assert linked["resolution_status"] == "closed"
    assert linked["resolution_evidence"]["linked_event_id"] == "sec_submissions:active"
    assert "resolution_evidence" not in untouched
    assert links[0]["matched_event_ids"] == ["sec_submissions:active"]


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
