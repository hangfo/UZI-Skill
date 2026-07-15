"""Regression tests for flow and data-contract bug fixes."""
from __future__ import annotations

import importlib.util
import sys
import webbrowser
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

SCRIPTS = Path(__file__).resolve().parent.parent
ROOT = SCRIPTS.parent.parent.parent
sys.path.insert(0, str(SCRIPTS))


def _load_root_run_module():
    spec = importlib.util.spec_from_file_location("uzi_root_run_for_tests", ROOT / "run.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    old_cwd = Path.cwd()
    try:
        spec.loader.exec_module(mod)
    finally:
        # run.py changes cwd on import; keep pytest cwd stable for later tests.
        import os
        os.chdir(old_cwd)
    return mod


def test_direct_report_path_takes_precedence_for_fund_summary(tmp_path):
    """Fund/versus/portfolio reports must reuse the generated HTML path."""
    mod = _load_root_run_module()
    summary = tmp_path / "fund-summary.html"
    summary.write_text("<html>summary</html>", encoding="utf-8")
    args = SimpleNamespace(_direct_report_path=summary)

    report_dir, standalone = mod._resolve_report_artifact(args, mod.SCRIPTS_DIR, "510300.SH")

    assert standalone == summary
    assert report_dir == tmp_path


def test_direct_report_uses_shared_post_process(monkeypatch, tmp_path):
    """Fund/versus/portfolio paths must reach the shared post-process hook."""
    mod = _load_root_run_module()
    summary = tmp_path / "fund-summary.html"
    summary.write_text("<html>summary</html>", encoding="utf-8")
    args = SimpleNamespace(_direct_report_path=summary, ticker="510300.SH")
    seen = []
    monkeypatch.setattr(
        mod,
        "_post_process_report",
        lambda got_args, env, report_dir, standalone: seen.append(
            (got_args, env, report_dir, standalone)
        ),
    )

    mod._post_process_direct_report(args, {"has_browser": False})

    assert len(seen) == 1
    assert seen[0][2] == tmp_path
    assert seen[0][3] == summary


def test_cloudflare_tunnel_does_not_auto_install_without_opt_in(monkeypatch):
    """--remote should not install packages or call sudo unless explicitly requested."""
    mod = _load_root_run_module()
    calls = []

    monkeypatch.setattr(mod.shutil, "which", lambda _name: None)
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **kw: calls.append((a, kw)))

    public_url, proc = mod.start_cloudflare_tunnel(8976, install=False)

    assert public_url is None
    assert proc is None
    assert calls == []


def test_no_open_report_suppresses_browser_even_when_available(monkeypatch, tmp_path):
    """--no-open-report is a hard local/remote browser boundary."""
    mod = _load_root_run_module()
    report = tmp_path / "report.html"
    report.write_text("<html>report</html>", encoding="utf-8")
    args = SimpleNamespace(
        output_dir=None,
        no_open_report=True,
        no_browser=False,
        remote=False,
        ticker="TEST",
        depth="lite",
    )
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url))

    mod._post_process_report(args, {"has_browser": True}, tmp_path, report)

    assert opened == []


def test_remote_shutdown_always_cleans_server_and_tunnel(monkeypatch):
    """Ctrl+C must close the HTTP server and reap the tunnel process."""
    mod = _load_root_run_module()

    class InterruptingEvent:
        def wait(self):
            raise KeyboardInterrupt

    class FakeServer:
        shutdown_called = False
        close_called = False

        def shutdown(self):
            self.shutdown_called = True

        def server_close(self):
            self.close_called = True

    class FakeTunnel:
        terminate_called = False
        wait_timeout = None

        def poll(self):
            return None

        def terminate(self):
            self.terminate_called = True

        def wait(self, timeout):
            self.wait_timeout = timeout

    server = FakeServer()
    tunnel = FakeTunnel()
    monkeypatch.setattr(mod.threading, "Event", lambda: InterruptingEvent())

    mod.wait_for_remote_shutdown(server, tunnel)

    assert server.shutdown_called is True
    assert server.close_called is True
    assert tunnel.terminate_called is True
    assert tunnel.wait_timeout == 5


def test_remote_post_process_forwards_install_opt_in(monkeypatch, tmp_path):
    """Remote post-processing must forward opt-in and hand cleanup the same objects."""
    mod = _load_root_run_module()
    report = tmp_path / "report.html"
    report.write_text("<html>report</html>", encoding="utf-8")
    args = SimpleNamespace(
        output_dir=None,
        no_open_report=True,
        no_browser=True,
        remote=True,
        ticker="TEST",
        depth="lite",
        port=8976,
        install_cloudflared=True,
    )
    server = object()
    tunnel = object()
    seen = {}
    monkeypatch.setattr(mod, "serve_report", lambda standalone, port: server)

    def fake_tunnel(port, install=False):
        seen["tunnel_args"] = (port, install)
        return "https://example.trycloudflare.com", tunnel

    monkeypatch.setattr(mod, "start_cloudflare_tunnel", fake_tunnel)
    monkeypatch.setattr(
        mod,
        "wait_for_remote_shutdown",
        lambda got_server, got_tunnel=None: seen.update(
            server=got_server, tunnel=got_tunnel
        ),
    )

    mod._post_process_report(args, {"has_browser": False}, tmp_path, report)

    assert seen["tunnel_args"] == (8976, True)
    assert seen["server"] is server
    assert seen["tunnel"] is tunnel


def test_agent_analysis_errors_fall_back_to_script_stub():
    """Structural agent_analysis errors must be discarded before synthesis merge."""
    import run_real_test as rrt

    bad = {"agent_reviewed": True, "dim_commentary": ["bad"], "narrative_override": ["bad"]}
    cleaned, issues = rrt._validate_agent_analysis_or_fallback(bad, "600519.SH")

    assert cleaned is None
    assert any(i.severity == "error" for i in issues)


def test_financials_exposes_ocf_fields():
    """Operating cash flow must not be hidden behind the fcf field only."""
    import fetch_financials as ff

    out = {"net_profit_history": [10.0]}
    df_cf = pd.DataFrame({"经营活动产生的现金流量净额": [12e8, 8e8]})

    ff._apply_operating_cash_flow(out, df_cf)

    assert out["ocf"] == "12.0亿"
    assert out["operating_cash_flow_yi"] == 12.0
    assert out["ocf_history"] == [12.0, 8.0]
    assert out["ocf_to_net_income_ratio"] == 1.2
    assert out["financial_health"]["ocf_to_net_income_ratio"] == 1.2
    assert "fcf" not in out
    assert "fcf_margin" not in out["financial_health"]


def test_financials_preserves_zero_as_latest_ocf():
    """A real zero OCF must not be replaced by an older non-zero period."""
    import fetch_financials as ff

    out = {"net_profit_history": [10.0]}
    df_cf = pd.DataFrame({"经营活动产生的现金流量净额": [0, "—", 8e8]})

    ff._apply_operating_cash_flow(out, df_cf)

    assert out["ocf"] == "0.0亿"
    assert out["operating_cash_flow_yi"] == 0.0
    assert out["ocf_history"] == [0.0, 8.0]
    assert out["ocf_to_net_income_ratio"] == 0.0


def test_financials_current_em_schema_aligns_annual_ocf_ratio():
    """Real 2026 Eastmoney schema: latest quarter display, annual ratio alignment."""
    import fetch_financials as ff

    out = {
        "financial_years": ["2024", "2025"],
        "net_profit_history": [862.28, 823.2],
    }
    # Field names and values are frozen from the live 600519 response on 2026-07-14.
    df_cf = pd.DataFrame(
        {
            "REPORT_DATE": ["2024-12-31", "2026-03-31", "2025-12-31"],
            "REPORT_TYPE": ["年报", "一季报", "年报"],
            "NETCASH_OPERATE": [92463692168.43, 26909891269.13, 61522204989.35],
            "CONSTRUCT_LONG_ASSET": [4678712000.0, 604791600.0, 3127595000.0],
        }
    )

    ff._apply_operating_cash_flow(out, df_cf)

    assert out["ocf"] == "269.1亿"
    assert out["ocf_source_field"] == "NETCASH_OPERATE"
    assert out["ocf_latest_period"] == "2026-03-31"
    assert out["ocf_latest_is_annual"] is False
    assert out["ocf_history_years"] == ["2024", "2025"]
    assert out["ocf_history"] == [924.64, 615.22]
    assert out["ocf_to_net_income_ratio"] == 0.75
    assert out["ocf_to_net_income_ratio_period"] == "2025"
    assert out["ocf_to_net_income_ratio_basis"] == "same_fiscal_year_annual_ocf_to_net_income"
    assert out["free_cash_flow_history_years"] == ["2024", "2025"]
    assert out["free_cash_flow_history"] == [877.85, 583.95]
    assert out["free_cash_flow_yi"] == 583.95
    assert out["free_cash_flow_period"] == "2025"
    assert out["free_cash_flow_basis"] == "reported_ocf_minus_cash_paid_for_long_term_assets"
    assert out["free_cash_flow_currency"] == "CNY"
    assert out["free_cash_flow_source_fields"]["cash_capex"] == "CONSTRUCT_LONG_ASSET"
    assert "fcf" not in out


def test_us_cashflow_schema_preserves_real_negative_fcf():
    """Frozen from live MSTR yfinance cash flow on 2026-07-14."""
    import fetch_financials as ff

    cashflow = pd.DataFrame(
        {
            pd.Timestamp("2025-12-31"): [-22579540000.0, -22512300000.0, -67241000.0],
            pd.Timestamp("2024-12-31"): [-22139270000.0, -22086240000.0, -53032000.0],
        },
        index=["Free Cash Flow", "Capital Expenditure", "Operating Cash Flow"],
    )
    out = {}

    ff._apply_us_free_cash_flow(out, cashflow, "USD")

    assert out["free_cash_flow_yi"] == -225.8
    assert out["free_cash_flow_period"] == "2025-12-31"
    assert out["free_cash_flow_history"] == [-221.39, -225.8]
    assert out["free_cash_flow_basis"] == "yfinance_cashflow_free_cash_flow"
    assert out["free_cash_flow_is_derived"] is False
    assert out["free_cash_flow_currency"] == "USD"


def test_stock_features_reads_ocf_to_net_income_ratio():
    from lib.stock_features import extract_features

    raw = {
        "ticker": "TEST",
        "market": "A",
        "dimensions": {
            "0_basic": {"data": {"name": "测试", "price": 10, "market_cap_yi": 100}},
            "1_financials": {"data": {
                "net_profit_history": [10.0],
                "revenue_history": [100.0],
                "ocf_to_net_income_ratio": 0.42,
                "financial_health": {"debt_ratio": 20, "current_ratio": 2},
            }},
        },
    }

    features = extract_features(raw, raw["dimensions"])

    assert features["ocf_to_net_income_ratio"] == 0.42


def test_stock_features_preserves_canonical_zero_ocf_ratio():
    """A top-level zero ratio must win over a stale nested fallback value."""
    from lib.stock_features import extract_features

    raw = {
        "ticker": "TEST",
        "market": "A",
        "dimensions": {
            "0_basic": {"data": {"name": "测试", "price": 10, "market_cap_yi": 100}},
            "1_financials": {"data": {
                "net_profit_history": [10.0],
                "revenue_history": [100.0],
                "ocf_to_net_income_ratio": 0.0,
                "financial_health": {
                    "debt_ratio": 20,
                    "current_ratio": 2,
                    "ocf_to_net_income_ratio": 1.2,
                },
            }},
        },
    }

    features = extract_features(raw, raw["dimensions"])

    assert features["ocf_to_net_income_ratio"] == 0.0


def test_peers_self_only_fallback_when_industry_missing(monkeypatch):
    import fetch_peers

    monkeypatch.setenv("UZI_AUX_HEAVY", "1")
    monkeypatch.setattr(fetch_peers.ds, "fetch_basic", lambda _ti: {
        "name": "无行业公司",
        "price": 10,
        "pe_ttm": 20,
        "pb": 2,
        "industry": None,
    })

    result = fetch_peers.main("600519.SH")
    data = result["data"]

    assert result["fallback"] is True
    assert data["peer_table"][0]["is_self"] is True
    assert "industry" in data["fallback_reason"]


def test_valuation_uses_cninfo_market_fallback_when_industry_missing(monkeypatch):
    import fetch_financials
    import fetch_valuation

    monkeypatch.setattr(fetch_valuation.ds, "fetch_basic", lambda _ti: {
        "name": "无行业公司",
        "price": 10,
        "pe_ttm": 20,
        "pb": 2,
        "industry": None,
        "market_cap_raw": 100e8,
    })
    monkeypatch.setattr(fetch_financials, "main", lambda _ticker: {
        "data": {"net_profit_history": [10.0]}
    })
    monkeypatch.setattr(fetch_valuation.ak, "stock_zh_valuation_baidu", lambda *a, **kw: pd.DataFrame())
    monkeypatch.setattr(fetch_valuation.ak, "stock_industry_pe_ratio_cninfo", lambda *a, **kw: pd.DataFrame({
        "行业名称": ["行业A", "行业B"],
        "市盈率-加权": [15.0, 25.0],
    }))

    result = fetch_valuation.main("600519.SH")
    data = result["data"]

    assert data["industry_pe"] == "—"
    assert data["industry_pe_source"] == ""
    assert data["industry_pe_input_industry"] == ""
    assert data["market_pe_reference"] == "20.0"
    assert data["market_pe_reference_source"] == "cninfo:stock_industry_pe_ratio_cninfo"
    assert "不参与同行估值" in data["industry_pe_fallback_reason"]
    assert data["dcf_is_proxy"] is False
    assert data["dcf_input_basis"] == ""
    assert data["dcf_available"] is False
    assert data["dcf_unavailable_reason"] == "missing_explicit_fcf"
    assert "禁止" in data["dcf_warning"]


def test_valuation_prefers_cash_statement_fcf_over_profit_proxy(monkeypatch):
    """Frozen 600519 values: a valid cash-statement FCF must win over net profit."""
    import fetch_financials
    import fetch_valuation

    monkeypatch.setattr(fetch_valuation.ds, "fetch_basic", lambda _ti: {
        "name": "贵州茅台", "price": 1400, "pe_ttm": 14, "pb": 6,
        "industry": "白酒", "market_cap_raw": 1.7e12,
    })
    monkeypatch.setattr(fetch_financials, "main", lambda _ticker: {"data": {
        "net_profit_history": [823.2],
        "financial_years": ["2025"],
        "free_cash_flow_yi": 583.95,
        "free_cash_flow_period": "2025",
        "free_cash_flow_basis": "reported_ocf_minus_cash_paid_for_long_term_assets",
        "free_cash_flow_source_fields": {
            "operating_cash_flow": "NETCASH_OPERATE",
            "cash_capex": "CONSTRUCT_LONG_ASSET",
        },
    }})
    monkeypatch.setattr(fetch_valuation.ak, "stock_zh_valuation_baidu", lambda *a, **kw: pd.DataFrame())
    monkeypatch.setattr(fetch_valuation.ak, "stock_industry_pe_ratio_cninfo", lambda *a, **kw: pd.DataFrame())

    data = fetch_valuation.main("600519.SH")["data"]

    assert data["dcf_is_proxy"] is False
    assert data["dcf_input_value_yi"] == 583.95
    assert data["dcf_input_basis"] == "reported_ocf_minus_cash_paid_for_long_term_assets"
    assert data["dcf_simple"]["input_contract"]["is_proxy"] is False
    assert data["dcf_input_source_fields"]["cash_capex"] == "CONSTRUCT_LONG_ASSET"
    assert data["dcf_currency"] == "CNY"
    assert data["dcf"].startswith("¥")


def test_negative_cash_statement_fcf_never_falls_back_to_positive_profit_proxy(monkeypatch):
    """Real MSTR negative FCF must make DCF unavailable, not manufacture value."""
    import fetch_financials
    import fetch_valuation

    monkeypatch.setattr(fetch_valuation.ds, "fetch_basic", lambda _ti: {
        "name": "Strategy", "price": 400, "pe_ttm": None, "pb": 2,
        "industry": "Software", "market_cap_raw": 1e11,
    })
    monkeypatch.setattr(fetch_financials, "main", lambda _ticker: {"data": {
        "net_profit_history": [100.0],
        "financial_years": ["2025"],
        "free_cash_flow_yi": -225.8,
        "free_cash_flow_period": "2025-12-31",
        "free_cash_flow_basis": "yfinance_cashflow_free_cash_flow",
        "free_cash_flow_currency": "USD",
    }})

    data = fetch_valuation.main("MSTR")["data"]

    assert data["dcf"] == "—"
    assert data["dcf_is_proxy"] is False
    assert data["dcf_input_value_yi"] == -225.8
    assert data["dcf_simple"]["intrinsic_value"] is None
    assert data["dcf_sensitivity"] == {}
    assert data["dcf_currency"] == "USD"
    assert fetch_valuation._currency_prefix("USD") == "US$"


def test_valuation_rejects_financial_institution_and_cross_currency_fcf(monkeypatch):
    import fetch_financials
    import fetch_valuation

    monkeypatch.setattr(fetch_valuation.ak, "stock_zh_valuation_baidu", lambda *a, **kw: pd.DataFrame())
    monkeypatch.setattr(fetch_valuation.ak, "stock_industry_pe_ratio_cninfo", lambda *a, **kw: pd.DataFrame())

    monkeypatch.setattr(fetch_valuation.ds, "fetch_basic", lambda _ti: {
        "name": "Bank", "price": 10, "industry": "Banks - Diversified",
        "currency": "USD", "market_cap_raw": 100e8,
    })
    monkeypatch.setattr(fetch_financials, "main", lambda _ticker: {"data": {
        "free_cash_flow_yi": 100.0, "free_cash_flow_currency": "USD",
    }})
    financial = fetch_valuation.main("JPM")["data"]
    assert financial["dcf_available"] is False
    assert financial["dcf_unavailable_reason"] == "not_applicable_financial_institution"

    monkeypatch.setattr(fetch_valuation.ds, "fetch_basic", lambda _ti: {
        "name": "Tencent", "price": 500, "industry": "Internet Content",
        "currency": "HKD", "market_cap_raw": 4e12,
    })
    monkeypatch.setattr(fetch_financials, "main", lambda _ticker: {"data": {
        "free_cash_flow_yi": 1901.71, "free_cash_flow_currency": "CNY",
        "free_cash_flow_period": "2025-12-31",
        "free_cash_flow_basis": "yfinance_cashflow_free_cash_flow",
    }})
    mismatch = fetch_valuation.main("00700.HK")["data"]
    assert mismatch["dcf_available"] is False
    assert mismatch["dcf_unavailable_reason"] == "cashflow_quote_currency_mismatch_requires_fx"
    assert mismatch["dcf_sensitivity"] == {}


def test_valuation_viz_discloses_fcf_input_and_escapes_warning():
    from lib.report.dim_viz import _viz_valuation

    rendered = _viz_valuation({
        "pe": "14",
        "industry_pe": "18",
        "dcf": "¥12882.0亿",
        "dcf_is_proxy": False,
        "dcf_input_basis": "reported_ocf_minus_cash_paid_for_long_term_assets",
        "dcf_input_period": "2025",
        "dcf_input_value_yi": 583.95,
        "dcf_currency": "CNY",
        "dcf_warning": "简化模型 <script>alert(1)</script>",
    })

    assert "DCF 输入·现金流量表 FCF" in rendered
    assert "2025" in rendered and "583.95亿 CNY" in rendered
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_fund_stats_budget_requires_explicit_unbounded_opt_in():
    from fetch_fund_holders import _bounded_fund_stats_budget

    assert _bounded_fund_stats_budget(20, hard_cap=50) == 20
    assert _bounded_fund_stats_budget(993, hard_cap=50) == 50
    assert _bounded_fund_stats_budget(993, hard_cap=50, allow_unbounded=True) == 993
    assert _bounded_fund_stats_budget(-1, hard_cap=50) == 0


def test_pipeline_routes_mutual_fund_to_legacy(monkeypatch):
    """Mutual funds must not enter the stock collector/fund-holding loop in pipeline."""
    from lib import market_router
    from lib.pipeline import run as pipeline_run

    monkeypatch.setattr(market_router, "is_chinese_name", lambda _ticker: False)
    monkeypatch.setattr(
        market_router,
        "parse_ticker",
        lambda _ticker: SimpleNamespace(market="A", code="110011"),
    )
    monkeypatch.setattr(market_router, "classify_security_type", lambda _code: "mutual_fund")

    try:
        pipeline_run._preflight_guards("110011")
    except ValueError as exc:
        assert "mutual_fund" in str(exc)
        assert "legacy" in str(exc)
    else:
        raise AssertionError("mutual fund must route to legacy before pipeline collection")


def test_expected_pipeline_fallback_has_dedicated_exception_contract():
    from lib.pipeline import run as pipeline_run

    assert issubclass(pipeline_run.PipelineFallback, ValueError)
    source = (ROOT / "run.py").read_text(encoding="utf-8")
    assert "except PipelineFallback as e:" in source
    assert "预期分流到 legacy" in source


def test_registry_matches_legacy_output_shapes():
    from lib.pipeline.fetchers.registry import FETCHER_REGISTRY
    from lib.pipeline.schema import DimResult
    from lib.pipeline.validators import validate_result

    cases = {
        "1_financials": {
            "roe": "18.0%",
            "net_margin": "10.0%",
            "revenue_growth": "+5.0%",
            "gross_margin": "30.0%",
            "financial_health": {"debt_ratio": 40, "current_ratio": 2.0, "fcf_margin": 80},
            "ocf": "12.0亿",
            "ocf_history": [12.0, 8.0],
            "ocf_to_net_income_ratio": 1.2,
            "free_cash_flow_yi": 10.0,
            "free_cash_flow_history": [8.0, 10.0],
            "free_cash_flow_history_years": ["2024", "2025"],
            "free_cash_flow_basis": "reported_ocf_minus_cash_paid_for_long_term_assets",
            "free_cash_flow_period": "2025",
            "free_cash_flow_currency": "CNY",
            "free_cash_flow_source_fields": {
                "operating_cash_flow": "NETCASH_OPERATE",
                "cash_capex": "CONSTRUCT_LONG_ASSET",
            },
        },
        "10_valuation": {
            "pe": "20.0",
            "pb": "3.0",
            "pe_quantile": "5 年 60 分位",
            "pb_quantile": "50%",
            "industry_pe": "25.0",
            "dcf": "¥100.0亿",
        },
    }
    for dim_key, data in cases.items():
        spec = FETCHER_REGISTRY[dim_key].spec
        result = validate_result(DimResult(dim_key=dim_key, data=data), spec)
        assert result.data_gaps == []
        if dim_key == "1_financials":
            for key in ("free_cash_flow_yi", "free_cash_flow_history", "free_cash_flow_basis", "free_cash_flow_period"):
                assert key in spec.optional_fields


def test_stock_features_normalizes_legacy_us_raw_market_cap_and_uses_real_fcf():
    from lib.stock_features import extract_features

    raw = {
        "ticker": "AAPL",
        "dimensions": {
            "0_basic": {"data": {
                "code": "AAPL", "price": 314.86,
                "market_cap": 4_624_460_808_192,
                "total_shares": 14_687_356_000,
                "total_shares_source": "yfinance.info.sharesOutstanding",
                "industry": "Consumer Electronics",
            }},
            "1_financials": {"data": {
                "net_profit_history": [1120.10],
                "free_cash_flow_yi": 987.67,
                "free_cash_flow_period": "2025-09-30",
                "free_cash_flow_basis": "yfinance_cashflow_free_cash_flow",
                "free_cash_flow_currency": "USD",
                "financial_health": {"total_debt": 847.11, "cash": 685.07},
            }},
        },
    }
    features = extract_features(raw, raw["dimensions"])

    assert round(features["market_cap_yi"], 2) == 46244.61
    assert round(features["shares_outstanding_yi"], 3) == 146.874
    assert features["shares_crosscheck_ok"] is True
    assert features["fcf_latest_yi"] == 987.67
    assert features["fcf_input_basis"] == "yfinance_cashflow_free_cash_flow"
    assert features["net_debt_bridge_available"] is True


def test_stock_features_preserves_explicit_negative_fcf_without_profit_proxy():
    from lib.stock_features import extract_features

    raw = {
        "ticker": "MSTR",
        "dimensions": {
            "0_basic": {"data": {
                "code": "MSTR", "price": 97.58, "market_cap": "353.8亿",
                "industry": "Software - Application",
            }},
            "1_financials": {"data": {
                "net_profit_history": [100.0],
                "free_cash_flow_yi": -225.8,
                "free_cash_flow_period": "2025-12-31",
                "free_cash_flow_basis": "yfinance_cashflow_free_cash_flow",
                "free_cash_flow_currency": "USD",
                "financial_health": {"total_debt": 82.57, "cash": 22.07},
            }},
        },
    }
    features = extract_features(raw, raw["dimensions"])
    assert features["fcf_available"] is True
    assert features["fcf_latest_yi"] == -225.8


def test_institutional_dcf_fails_closed_for_unsafe_inputs():
    from lib.fin_models import compute_dcf

    base = {
        "market": "A",
        "price": 100, "market_cap_yi": 1000, "shares_outstanding_yi": 10,
        "fcf_available": True, "fcf_latest_yi": 50,
        "fcf_input_basis": "cash_statement", "fcf_input_period": "2025",
        "fcf_input_currency": "USD", "quote_currency": "USD",
        "net_debt_bridge_available": True, "total_debt_yi": 20, "cash_yi": 10,
    }
    assert compute_dcf({**base, "fcf_latest_yi": -1})["reason"] == "non_positive_explicit_fcf"
    assert compute_dcf({**base, "fcf_available": False, "fcf_latest_yi": None})["available"] is False
    assert compute_dcf({**base, "dcf_is_financial_institution": True})["reason"] == "not_applicable_financial_institution"
    assert compute_dcf({**base, "net_debt_bridge_available": False})["reason"] == "missing_debt_or_cash_for_equity_bridge"
    assert compute_dcf({**base, "quote_currency": "HKD"})["reason"] == "cashflow_quote_currency_mismatch_requires_fx"
    assert compute_dcf({**base, "market": "U"})["reason"] == "unsupported_market_discount_rate_contract"

    valid = compute_dcf(base)
    assert valid["available"] is True
    assert valid["base_fcf_yi"] == 50
    assert valid["input_contract"]["is_proxy"] is False


def test_simple_dcf_rejects_terminal_growth_at_or_above_wacc():
    from fetch_valuation import simple_dcf

    result = simple_dcf(100, growth_terminal=0.10, wacc=0.10)
    assert result["intrinsic_value_total"] is None
    assert "WACC must exceed terminal growth" in result["_note"]


def test_institutional_renderer_discloses_fail_closed_reason():
    from lib.report.institutional import _render_dcf_block

    rendered = _render_dcf_block({"dcf": {
        "available": False,
        "reason": "missing_debt_or_cash_for_equity_bridge<script>",
    }})
    assert "DCF unavailable (fail-closed)" in rendered
    assert "missing_debt_or_cash_for_equity_bridge" in rendered
    assert "<script>" not in rendered
