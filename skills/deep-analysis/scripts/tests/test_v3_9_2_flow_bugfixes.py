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
    assert data["market_pe_reference"] == "20.0"
    assert "不参与同行估值" in data["industry_pe_fallback_reason"]


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
