# US momentum history shadow

- fetched_at_utc: `2026-07-20T06:39:58.287650+00:00`
- baseline: `2fdc8b4ca3498fe2621cb5f0aa95f84eaf0fa80f`
- candidate: `a8a804d3b02699b2b8754bbe11b0f2786a96dc92`
- real tickers: `MU, WDC, STX, SNDK, GEV, BMNR, CRCL, FIG, SPCX`
- rows: `49`; no_change `7`; beneficial_contract_fix `42`; possible_regression `0`
- process seconds: baseline `4.454`, candidate `4.130`
- pure-compute median seconds: baseline `0.092015`, candidate `0.087824`; warning `False`

| ticker | window | as of | baseline stage | candidate stage | verdict |
|---|---:|---|---:|---:|---|
| MU | 60 | 2024-10-10 | 3 | 0 | beneficial_contract_fix |
| MU | 90 | 2024-11-21 | 3 | 0 | beneficial_contract_fix |
| MU | 120 | 2025-01-07 | 2 | 0 | beneficial_contract_fix |
| MU | 180 | 2025-04-04 | 4 | 0 | beneficial_contract_fix |
| MU | 200 | 2025-05-05 | 4 | 4 | beneficial_contract_fix |
| MU | full | 2026-07-17 | 2 | 2 | no_change |
| WDC | 60 | 2024-10-10 | 4 | 0 | beneficial_contract_fix |
| WDC | 90 | 2024-11-21 | 2 | 0 | beneficial_contract_fix |
| WDC | 120 | 2025-01-07 | 1 | 0 | beneficial_contract_fix |
| WDC | 180 | 2025-04-04 | 4 | 0 | beneficial_contract_fix |
| WDC | 200 | 2025-05-05 | 4 | 4 | beneficial_contract_fix |
| WDC | full | 2026-07-17 | 2 | 2 | no_change |
| STX | 60 | 2024-10-10 | 3 | 0 | beneficial_contract_fix |
| STX | 90 | 2024-11-21 | 1 | 0 | beneficial_contract_fix |
| STX | 120 | 2025-01-07 | 4 | 0 | beneficial_contract_fix |
| STX | 180 | 2025-04-04 | 4 | 0 | beneficial_contract_fix |
| STX | 200 | 2025-05-05 | 4 | 4 | beneficial_contract_fix |
| STX | full | 2026-07-17 | 2 | 2 | no_change |
| SNDK | 60 | 2025-05-09 | 1 | 0 | beneficial_contract_fix |
| SNDK | 90 | 2025-06-24 | 3 | 0 | beneficial_contract_fix |
| SNDK | 120 | 2025-08-06 | 1 | 0 | beneficial_contract_fix |
| SNDK | 180 | 2025-10-30 | 2 | 0 | beneficial_contract_fix |
| SNDK | 200 | 2025-11-28 | 2 | 2 | beneficial_contract_fix |
| SNDK | full | 2026-07-17 | 2 | 2 | no_change |
| GEV | 60 | 2024-10-10 | 2 | 0 | beneficial_contract_fix |
| GEV | 90 | 2024-11-21 | 2 | 0 | beneficial_contract_fix |
| GEV | 120 | 2025-01-07 | 2 | 0 | beneficial_contract_fix |
| GEV | 180 | 2025-04-04 | 1 | 0 | beneficial_contract_fix |
| GEV | 200 | 2025-05-05 | 2 | 2 | beneficial_contract_fix |
| GEV | full | 2026-07-17 | 2 | 2 | no_change |
| BMNR | 60 | 2025-08-29 | 2 | 0 | beneficial_contract_fix |
| BMNR | 90 | 2025-10-13 | 2 | 0 | beneficial_contract_fix |
| BMNR | 120 | 2025-11-24 | 1 | 0 | beneficial_contract_fix |
| BMNR | 180 | 2026-02-23 | 4 | 0 | beneficial_contract_fix |
| BMNR | 200 | 2026-03-23 | 4 | 4 | beneficial_contract_fix |
| BMNR | full | 2026-07-17 | 4 | 4 | no_change |
| CRCL | 60 | 2025-08-29 | 1 | 0 | beneficial_contract_fix |
| CRCL | 90 | 2025-10-13 | 4 | 0 | beneficial_contract_fix |
| CRCL | 120 | 2025-11-24 | 4 | 0 | beneficial_contract_fix |
| CRCL | 180 | 2026-02-23 | 4 | 0 | beneficial_contract_fix |
| CRCL | 200 | 2026-03-23 | 3 | 3 | beneficial_contract_fix |
| CRCL | full | 2026-07-17 | 4 | 4 | no_change |
| FIG | 60 | 2025-10-23 | 4 | 0 | beneficial_contract_fix |
| FIG | 90 | 2025-12-05 | 4 | 0 | beneficial_contract_fix |
| FIG | 120 | 2026-01-21 | 4 | 0 | beneficial_contract_fix |
| FIG | 180 | 2026-04-17 | 4 | 0 | beneficial_contract_fix |
| FIG | 200 | 2026-05-15 | 4 | 4 | beneficial_contract_fix |
| FIG | full | 2026-07-17 | 4 | 4 | beneficial_contract_fix |
| SPCX | full | 2026-07-17 | 0 | 0 | beneficial_contract_fix |

The bars are real Yahoo daily observations fetched once and replayed identically in both worktrees. Short windows are historical snapshots of those real series, not generated prices.
