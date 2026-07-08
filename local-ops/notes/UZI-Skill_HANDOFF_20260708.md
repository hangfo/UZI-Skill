# UZI-Skill Handoff - 2026-07-08

## Current Windows State

- Repo: `D:\UZI-Skill`
- Branch: `codex/scoring-validation-guardrails`
- HEAD: `5cf86467f72211c6337688aae0e9502a871c35aa`
- Remote: `origin/codex/scoring-validation-guardrails`
- Working tree: clean as of 2026-07-08

## What Was Completed

Replit HEAD scoring fixes were imported into Windows, then hardened with extra
edge-case tests.

Included commits after `codex/windows-local-stable`:

1. `dc3ef4c` - P0/P1/P2 scoring fixes and score drift tracker
2. `32a0bc2` - score drift schema fix and scoring consistency tests
3. `59f3a53` - comprehensive scoring consistency tests and score pipeline enhancements
4. `5cf8646` - Windows follow-up hardening for edge-case regression tests

Key behavior now covered:

- `recent_news` is canonical. If present but empty, it does not fall back to stale legacy `news`.
- Severe negative events can lower event score even if only one item appears.
- Dynamic `POLARIZE_K` formula is unchanged, but diagnostics now expose:
  - `polarize_stdev`
  - `polarize_active_count`
  - `polarize_skip_count`
- Stage 3 no-price cap test now checks the real guardrail path.
- Old fixed-K smoke test now validates dynamic-K behavior.
- Replit zip attachment noise was removed from final tree.

## Validation Already Done On Windows

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

Core basket:

| ticker | buy_score | read |
|---|---:|---|
| AAPL | 68 | strong quality, valuation constrained |
| 600519.SH | 59 | high quality, buy point constrained |
| 00700.HK | 59 | high quality, trend/drawdown constrained |
| MSTR | 34-36 | risk/quality guardrails active |
| AXTI | 32 | speculative small-cap constrained |

Holdout:

| ticker | buy_score | read |
|---|---:|---|
| CRCL | 33-35 | avoid |
| SIVE.ST | 36 | avoid |
| 688017.SH | 55-58 | cautious observation |

## Mac Sync Prompt

Use this on Mac Codex App:

```text
Continue UZI-Skill. Sync remote branch:

origin/codex/scoring-validation-guardrails

If the branch does not exist locally:
git fetch origin codex/scoring-validation-guardrails
git checkout -b codex/scoring-validation-guardrails origin/codex/scoring-validation-guardrails

If it already exists locally:
git fetch origin
git checkout codex/scoring-validation-guardrails
git pull --ff-only

Do not reinstall. Do not run deep. Do not run update. Use the project local Python/venv.
After syncing, verify:
1. working tree clean
2. py_compile key scoring files
3. direct-run scoring consistency tests if pytest is unavailable
4. lite/medium regression basket
5. holdout CRCL, SIVE.ST, 688017.SH if cache exists

Expected HEAD:
5cf86467f72211c6337688aae0e9502a871c35aa
```

## Recommended Next Priority

Do not tune scoring weights next unless a neutral validation harness shows a
decision-quality regression.

Recommended order:

1. Build a neutral model-comparison harness that compares baseline branch
   `codex/windows-local-stable` against current branch
   `codex/scoring-validation-guardrails` on the same cached raw inputs.
2. Extend holdout coverage with frozen examples across A/H/US/EU/JP/TW if cache
   exists or with small synthetic fixtures when cache is missing.
3. Add data-quality coefficient design behind tests, but do not merge it into
   scoring until comparison shows improved decision behavior.
4. Improve HTML readability after scoring validation is stable.
5. Only then consider formula/weight tuning.

## Boundary Rules For Next Session

- No reinstall.
- No deep run unless explicitly requested.
- No update script.
- Keep Windows/Mac compatibility.
- Prefer cached raw data and pure scoring tests before any new network fetch.
- Every formula change needs:
  - monotonic test
  - adversarial test
  - branch-vs-branch comparison
  - lite/medium basket check
  - holdout check
