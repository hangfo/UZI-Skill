# Branch Score Comparison Harness

Date: 2026-07-08

## Purpose

This harness compares two git refs with the same cached inputs before any
scoring formula change is accepted. It is intentionally neutral: it does not
fetch new data, does not run deep analysis, and does not tune weights.

The primary question is:

> Did the candidate branch change a buy/sell decision in a way that violates
> the case's decision boundary?

## Current Baseline

- Baseline ref: `codex/windows-local-stable`
- Candidate ref: `codex/scoring-validation-guardrails`
- Default command:

```powershell
D:\UZI-Skill\.venv\Scripts\python.exe tools\branch_score_compare.py `
  --baseline codex/windows-local-stable `
  --candidate codex/scoring-validation-guardrails `
  --mode both `
  --include-holdout `
  --label 20260708-core-holdout-both `
  --runner-timeout 600
```

Outputs are local validation artifacts under:

```text
local-ops/state/branch-score-compare/
```

`local-ops/` is intentionally local on this Windows machine. The reusable tool
and tests live in tracked paths:

- `tools/branch_score_compare.py`
- `skills/deep-analysis/scripts/tests/test_branch_score_compare.py`

## Boundaries

- Do not reinstall dependencies.
- Do not run update scripts.
- Do not run `--depth deep`.
- Do not fetch fresh market data for this comparison.
- Prefer cached `raw_data.json` and pure scoring functions.
- Do not push to upstream `wbh604/UZI-Skill`; push only to the fork
  `hangfo/UZI-Skill`.
- Do not tune scoring formulas unless this harness or a similarly neutral test
  proves a decision-quality failure.

## Case Layers

### Cached Raw Data

The cached basket uses real local `.cache/<ticker>/raw_data.json` snapshots.

Core:

- `600519.SH`: A-share quality/value control.
- `00700.HK`: HK platform quality control.
- `AAPL`: US profitable mega-cap with valuation constraint.
- `MSTR`: crypto treasury / volatility risk control.
- `AXTI`: speculative small-cap adversarial control.

Holdout:

- `CRCL`: stablecoin / IPO volatility / regulatory catalyst.
- `SIVE.ST`: Swedish market compatibility, loss/high-valuation holdout.
- `688017.SH`: robotics reducer growth with valuation pressure.

### Synthetic Feature Cases

These cases call `compute_investment_score()` directly. They are designed to
stress decision boundaries without relying on network data.

- `theme_only_microcap`: hot theme, weak quality, extreme risk.
- `quality_compounder_no_momentum`: durable quality but weak trend/growth.
- `expensive_profitable_platform`: high quality, valuation pressure.
- `high_quality_stage3_confirmed_downtrend`: quality stock in confirmed Stage 3
  distribution/downtrend.
- `stage4_missing_price_high_quality`: Stage 4 quality stock with missing price
  confirmation.
- `a_share_youzi_heat_institutional_selling`: A-share youzi heat with weak
  fundamentals.
- `missing_financials_theme_heat`: missing fundamentals but high theme heat.

### Synthetic Raw Data Cases

These cases call the same `score_dimensions -> generate_panel ->
generate_synthesis` path as cached raw data. They cover field contracts and
data-quality boundaries that feature-only tests cannot see.

- `__synthetic_empty_recent_news_stale_legacy`: present-but-empty
  `recent_news` must not fall back to stale legacy `news`.
- `__synthetic_single_strong_negative_event`: one severe negative event must
  lower `15_events`.
- `__synthetic_negated_negative_event`: negated negative phrases such as
  "无违规" or "settled lawsuit" should not be penalized.
- `__synthetic_missing_financials_raw`: missing financials should not crash or
  promote a high-confidence buy.

## Verdicts

- `ok`: no decision boundary was violated.
- `review`: score drift or tier movement is large enough to inspect, but is not
  automatically a regression.
- `possible_regression`: the candidate branch violated a case-specific
  boundary, such as risk cases being upgraded or event hygiene failing.

Decision tiers:

| Tier | Score Range |
|---|---:|
| `avoid` | `< 40` |
| `cautious` | `40 <= score < 55` |
| `watch` | `55 <= score < 65` |
| `buy_candidate` | `65 <= score < 80` |
| `strong_buy` | `>= 80` |

## Regression Flags

Important flags include:

- `quality_control_downgrade`: quality control was downgraded by tier.
- `risk_control_upgrade`: risk control was upgraded by tier.
- `speculative_promoted_to_buy`: speculative watch case became buy/strong buy.
- `below_candidate_floor` / `above_candidate_ceiling`: candidate score crossed
  a case boundary.
- `15_events_below_floor` / `15_events_above_ceiling`: event dimension violated
  a synthetic raw-data contract.
- `large_score_drift`: absolute score delta is at least 8 points.
- `decision_tier_changed`: decision tier changed.

Only the first group of boundary violations is treated as
`possible_regression`. Large drift without a boundary violation is `review`.

## Last Known Result

Expanded run:

```text
label: 20260708-expanded-core-holdout-both
result: 29 ok / 2 review / 0 possible_regression
```

Output files:

```text
local-ops/state/branch-score-compare/20260708-expanded-core-holdout-both.md
local-ops/state/branch-score-compare/20260708-expanded-core-holdout-both.json
```

The two `review` rows are expected risk-convergence changes, not formula
regressions:

- `high_quality_stage3_confirmed_downtrend`: `66.0 -> 59.0`, tier
  `buy_candidate -> watch`.
- `stage4_missing_price_high_quality`: `66.0 -> 59.0`, tier
  `buy_candidate -> watch`.

Both represent the candidate branch preventing Stage 3/4 quality-floor style
false buy signals.

Synthetic raw-data checks also show the intended field-contract behavior:

- Empty canonical `recent_news` with stale legacy `news`: baseline
  `15_events=8`, candidate `15_events=5`.
- Single strong negative event: baseline `15_events=5`, candidate
  `15_events=4`.
- Negated negative event: baseline `15_events=5`, candidate `15_events=5`.
- Missing financials raw case: candidate stays `cautious`, not buy.

If future runs produce nonzero `possible_regression`, inspect the exact case
before changing any formula.
