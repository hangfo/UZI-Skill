from __future__ import annotations

import us_momentum_walkforward as umw


def test_selected_tickers_are_never_parameter_tuning_evidence():
    audit, membership = umw._universe_audit(None, ["NVDA", "TSLA"])
    assert audit["status"] == "selected_universe_only"
    assert audit["parameter_tuning_allowed"] is False
    assert membership == {}


def test_complete_point_in_time_manifest_can_pass():
    manifest = {
        "schema": "uzi.us_point_in_time_universe.v1",
        "source_type": "official_listing_archive",
        "source": "Example official archive",
        "source_url": "https://example.test/archive",
        "lookahead_free": True,
        "includes_delisted": True,
        "complete_universe": True,
        "memberships": [
            {"ticker": "LIVE", "effective_from": "2015-01-01"},
            {"ticker": "DEAD", "effective_from": "2015-01-01", "effective_to": "2020-06-30"},
        ],
    }
    audit, membership = umw._universe_audit(manifest, ["LIVE", "DEAD"])
    assert audit["status"] == "optimization_eligible"
    assert audit["parameter_tuning_allowed"] is True
    assert umw._membership_allows(membership, "DEAD", "2020-06-30") is True
    assert umw._membership_allows(membership, "DEAD", "2020-07-01") is False


def test_manifest_fails_closed_on_partial_or_no_delisted_coverage():
    manifest = {
        "schema": "uzi.us_point_in_time_universe.v1",
        "source_type": "official_listing_archive",
        "source": "Archive",
        "source_url": "https://example.test/archive",
        "lookahead_free": True,
        "includes_delisted": True,
        "complete_universe": True,
        "memberships": [{"ticker": "NVDA", "effective_from": "2015-01-01"}],
    }
    audit, _ = umw._universe_audit(manifest, ["NVDA", "TSLA"])
    assert audit["parameter_tuning_allowed"] is False
    assert any("missing" in reason for reason in audit["reasons"])
    assert any("delisted" in reason for reason in audit["reasons"])


def test_membership_filter_removes_post_delisting_signals():
    rows = [
        {"Date": f"2020-01-{day:02d}", "Open": 10 + day, "High": 11 + day,
         "Low": 9 + day, "Close": 10 + day, "Volume": 1000}
        for day in range(1, 11)
    ]
    membership = {"DEAD": [("2020-01-01", "2020-01-06")]}
    signals = umw._build_signals(
        {"DEAD": rows}, rows, horizons=[2], min_history=3,
        round_trip_cost_bps=20, membership=membership,
    )
    assert signals
    assert all(row["signal_date"] <= "2020-01-06" for row in signals)
