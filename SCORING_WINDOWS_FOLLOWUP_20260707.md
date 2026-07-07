# Scoring Windows Follow-up - 2026-07-07

This note records the Windows-side hardening after importing the Replit HEAD
scoring fixes into `codex/scoring-validation-guardrails`.

## Extra Boundary Fixes

1. `15_events.recent_news` is now treated as the canonical field when present.
   A present-but-empty `recent_news: []` no longer falls back to legacy `news`,
   because that can turn stale cached news into fresh evidence.
2. Event sentiment now lets a small number of severe negative events move the
   score below neutral. Fraud, accounting fraud, SEC charges, and investigation
   signals should affect buy/sell decisions without needing ten repeated news
   items. Total event penalty remains capped at 3 points.
3. `consensus_formula` now exposes `polarize_stdev`,
   `polarize_active_count`, and `polarize_skip_count`. The dynamic K formula is
   unchanged; this only improves drift observability.
4. Tests were tightened so they check real output paths and current dynamic-K
   behavior instead of stale assumptions.

## Tests Added Or Strengthened

- `test_p0b_empty_recent_news_does_not_fallback_to_stale_news`
- `test_p1c_genuine_negative_events_penalised` tightened from `<= 5` to `< 5`
- `test_p1c_single_strong_negative_event_penalised`
- `test_p2b_polarize_diagnostics_present`
- Stage 3 no-price test now reads `diagnostics.guardrails.falling_trend_cap`
- v2.15.4 school-score smoke test now accepts dynamic K and checks diagnostics

## Windows Validation

- `py_compile`: pass
- `test_scoring_consistency.py` direct harness: 26 passed, 0 failed
- `test_v2_15_4_school_scores.py` direct harness: 9 passed, 0 failed
- `local-ops/tools/scoring_regression_basket.py`: pass

Adversarial probes:

| case | dim_15 score |
|---|---:|
| two strong negative events | 4 |
| single strong negative event | 4 |
| empty canonical news with stale legacy news | 5 |
| 20 positive canonical news items | 7 |
| negated negative context | 5 |

Core basket snapshot:

| mode | ticker | overall | investment_score | read |
|---|---:|---:|---:|---|
| lite | 600519.SH | 51.9 | 59.0 | high quality, buy point constrained |
| lite | 00700.HK | 51.0 | 59.0 | high quality, trend/drawdown constrained |
| lite | AAPL | 49.9 | 68.0 | quality recognized, valuation constrained |
| lite | MSTR | 38.0 | 34.3 | quality/risk guardrails active |
| lite | AXTI | 43.8 | 31.9 | speculative small-cap risk constrained |

Holdout snapshot:

| mode | ticker | overall | investment_score | read |
|---|---:|---:|---:|---|
| lite | CRCL | 41.1 | 33.3 | avoid; falling-trend guardrail active |
| lite | SIVE.ST | 47.2 | 36.3 | avoid; loss/high-valuation guardrails active |
| lite | 688017.SH | 54.8 | 54.9 | cautious; growth high but valuation axis is 20 |
| medium | CRCL | 40.9 | 34.5 | avoid; stable conclusion |
| medium | SIVE.ST | 47.2 | 36.3 | avoid; stable conclusion |
| medium | 688017.SH | 56.6 | 57.8 | cautious; not overpromoted by growth |
