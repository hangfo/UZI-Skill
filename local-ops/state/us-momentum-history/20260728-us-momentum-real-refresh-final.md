# US momentum history shadow

- fetched_at_utc: `2026-07-28T07:31:33.128757+00:00`
- baseline: `e7241dcb96460459f4f3db8adb750a2f94ba4cb8`
- candidate: `1f5251cc2bb21dfc48a04c4fd79ac33c9b23850d`
- real tickers: `AAPL, AMD, HOOD, BMNR, MU, SNDK, SPCX`
- rows: `37`; no_change `37`; beneficial_contract_fix `0`; possible_regression `0`
- process seconds: baseline `3.832`, candidate `3.779`
- pure-compute median seconds: baseline `0.073388`, candidate `0.073262`; warning `False`

| ticker | window | as of | baseline stage | candidate stage | verdict |
|---|---:|---|---:|---:|---|
| AAPL | 60 | 2024-10-21 | 0 | 0 | no_change |
| AAPL | 90 | 2024-12-03 | 0 | 0 | no_change |
| AAPL | 120 | 2025-01-17 | 0 | 0 | no_change |
| AAPL | 180 | 2025-04-15 | 0 | 0 | no_change |
| AAPL | 200 | 2025-05-14 | 4 | 4 | no_change |
| AAPL | full | 2026-07-27 | 2 | 2 | no_change |
| AMD | 60 | 2024-10-21 | 0 | 0 | no_change |
| AMD | 90 | 2024-12-03 | 0 | 0 | no_change |
| AMD | 120 | 2025-01-17 | 0 | 0 | no_change |
| AMD | 180 | 2025-04-15 | 0 | 0 | no_change |
| AMD | 200 | 2025-05-14 | 4 | 4 | no_change |
| AMD | full | 2026-07-27 | 2 | 2 | no_change |
| HOOD | 60 | 2024-10-21 | 0 | 0 | no_change |
| HOOD | 90 | 2024-12-03 | 0 | 0 | no_change |
| HOOD | 120 | 2025-01-17 | 0 | 0 | no_change |
| HOOD | 180 | 2025-04-15 | 0 | 0 | no_change |
| HOOD | 200 | 2025-05-14 | 2 | 2 | no_change |
| HOOD | full | 2026-07-27 | 4 | 4 | no_change |
| BMNR | 60 | 2025-08-29 | 0 | 0 | no_change |
| BMNR | 90 | 2025-10-13 | 0 | 0 | no_change |
| BMNR | 120 | 2025-11-24 | 0 | 0 | no_change |
| BMNR | 180 | 2026-02-23 | 0 | 0 | no_change |
| BMNR | 200 | 2026-03-23 | 4 | 4 | no_change |
| BMNR | full | 2026-07-27 | 4 | 4 | no_change |
| MU | 60 | 2024-10-21 | 0 | 0 | no_change |
| MU | 90 | 2024-12-03 | 0 | 0 | no_change |
| MU | 120 | 2025-01-17 | 0 | 0 | no_change |
| MU | 180 | 2025-04-15 | 0 | 0 | no_change |
| MU | 200 | 2025-05-14 | 3 | 3 | no_change |
| MU | full | 2026-07-27 | 2 | 2 | no_change |
| SNDK | 60 | 2025-05-09 | 0 | 0 | no_change |
| SNDK | 90 | 2025-06-24 | 0 | 0 | no_change |
| SNDK | 120 | 2025-08-06 | 0 | 0 | no_change |
| SNDK | 180 | 2025-10-30 | 0 | 0 | no_change |
| SNDK | 200 | 2025-11-28 | 2 | 2 | no_change |
| SNDK | full | 2026-07-27 | 2 | 2 | no_change |
| SPCX | full | 2026-07-27 | 0 | 0 | no_change |

The bars are real Yahoo daily observations fetched once and replayed identically in both worktrees. Short windows are historical snapshots of those real series, not generated prices.
