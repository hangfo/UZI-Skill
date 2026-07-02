# UZI scoring model regression plan

Date: 2026-07-01
Source branch: `codex/windows-local-stable`
Mac sync branch: `codex/local-mac-stable`
Scope: Windows local validation imported into the Mac stable branch and
rechecked with the Mac `.venv`.

## Boundaries

- Do not reinstall dependencies.
- Do not run update scripts.
- Do not run `--depth deep`.
- Use the active platform's existing project virtualenv:
  - Windows source run: `D:\UZI-Skill\.venv\Scripts\python.exe`
  - Mac sync run: `source ~/UZI-Skill/.venv/bin/activate`
- Treat missing data as a data gap; do not silently invent defaults.
- Keep local validation artifacts in `local-ops/` unless they are promoted intentionally.

## First-principles objective

The score being tuned is `investment_score`, not the legacy panel-driven
`overall_score`.

`investment_score` should answer: is this stock attractive enough, at today's
quality, growth, catalyst, valuation, and risk profile, to enter formal research
or a buy/watch candidate list?

It should not merely measure report completeness, theme heat, or how many
investors are mechanically bullish.

## Current model contract

Five axes:

- Quality: durable profitability, margins, moat, FCF, balance sheet.
- Growth: revenue/profit growth and confirmed technical momentum.
- Catalyst: policy, analyst support, AI or industry catalyst, event path.
- Valuation: current odds after PE/PB/quantile/dividend context.
- Risk control: debt, drawdown, volatility, crowding, scam/promotion flags.

Current weights:

- Quality: 25%
- Growth: 17%
- Catalyst: 28%
- Valuation: 15%
- Risk control: 15%

Risk is also a gate. A weak company with weak risk control must not become a
high-ranked idea just because the theme is hot.

## Regression structure

Core basket:

- `600519.SH`: A-share quality/value control.
- `00700.HK`: HK platform quality control.
- `AAPL`: US profitable mega-cap with valuation constraint.
- `MSTR`: crypto treasury / volatility risk control.
- `AXTI`: speculative small-cap adversarial control.

Holdout candidates:

- `CRCL`: stablecoin / regulatory catalyst / IPO volatility.
- `688017.SH`: Leader Harmonious Drive, robotics reducer / high valuation / A-share technology manufacturing.
- `SIVE.ST`: Sivers Semiconductors, Swedish market compatibility probe first.

Synthetic adversarial cases:

- Theme-only microcap with negative margins and extreme YTD.
- Quality compounder with weak momentum.
- Expensive profitable platform with strong quality but valuation pressure.

## Convergence criteria

The model is considered converged for this local pass when:

- Core basket passes on both lite and medium views.
- Holdout results do not force a contradiction in the core basket.
- AXTI-like speculative names remain capped below quality mega-cap controls.
- Quality compounders are not forced into high-conviction buy ratings without growth or catalyst support.
- Small weight perturbations do not materially change tier ordering.
- Any failure is explained as either model logic, source data quality, or market-routing coverage.

## Quantitative optimization plan

Use a constrained grid, not manual percentage guessing:

- Keep quality between 20% and 30%.
- Keep growth between 12% and 24%.
- Keep catalyst between 18% and 32%.
- Keep valuation between 12% and 24%.
- Keep risk control between 12% and 24%.
- Normalize each candidate to 100%.

Score candidate weight sets by:

- Core basket pass/fail count.
- Tier-ordering violations.
- Holdout sanity violations.
- Adversarial failure count.
- Score dispersion: enough separation without unstable extremes.

Human judgment is only needed for coarse labels such as "formal research",
"watch", or "avoid". If human judgment is unavailable, use external proxy
standards: 6-12 month excess return, drawdown-adjusted return, profitability
durability, estimate revisions, valuation percentile, and known risk events.

## Next tasks

1. Preserve the current core baseline and after-change output. Done locally in `local-ops/state/scoring-regression/`.
2. Add a weight sensitivity runner over the core basket. Done locally in `local-ops/tools/scoring_weight_sensitivity.py`.
3. Run `CRCL` and `688017.SH` as holdout lite/medium tests. Done on 2026-07-01.
4. Probe `SIVE.ST` routing before using it as a scoring sample. Done on 2026-07-01; route global suffixes through `G` / yfinance first, then include scoring only after data quality is confirmed.
5. Add clear guardrail diagnostics to the scoring output. Done for `compute_investment_score`.
6. Promote only stable, cross-sample improvements into tracked code.

## 2026-07-01 holdout results

CRCL:

- Lite and medium both completed quickly.
- `investment_score` stayed near 39-40.
- Guardrail fired because quality is weak and risk control is poor.
- Interpretation: current model does not over-reward stablecoin/IPO/regulatory narrative.

688017.SH:

- Lite completed but was slow for a lite run because `0_basic` took about 64 seconds.
- Medium completed in about 577 seconds.
- Medium triggered a long `19_contests` loop over 859 items; this is a collection performance issue, not a scoring issue.
- Medium `investment_score` was about 58, with high growth but valuation compressed by PE/PB pressure.
- Interpretation: current model treats robotics reducer exposure as a watchlist/speculative growth case, not a high-conviction buy.

SIVE / SIVE.ST:

- `SIVE` routes like a US ticker.
- `SIVE.ST` originally misclassified as A-share style because `.ST` was not a supported market suffix.
- Current fix: route `.ST`, `.T`, `.TW`, `.TWO` and other Yahoo-style non-US suffixes as `G`, using yfinance-compatible data paths first.
- Interpretation: Sivers should remain a data-quality compatibility holdout before it becomes a scoring holdout.

Contest-source limiting:

- `19_contests` is an auxiliary sentiment/crowding signal, not a core quality or valuation input.
- The 859-item loop observed on `688017.SH` came from A-share contest/portfolio style sources where the stock has many public holder/search rows. US/foreign names often have little or no comparable Chinese contest coverage, so CRCL did not hit the same path.
- Medium now samples cheap contest evidence and skips heavy contest sources by default; deep can still run full/heavy evidence.
- Scoring interpretation: limiting should not materially change a buy/sell conclusion. If it does, the model is over-weighting noisy sentiment and should be fixed at the scoring layer, not by forcing every collection run to scrape hundreds of rows.

Temporary ideas evaluated:

- More conservative quality+risk-heavy weights produced better core dispersion, but also pushed 688017.SH lower. Keep as a candidate, not a production change, until more holdout samples are available.
- Fixing self-review `None` handling is feasible and low risk; promote it because it removes noisy warning crashes observed on 688017.SH without changing score math.

Priority backlog after this pass:

1. Confirm `19_contests` medium limiting on a fresh A-share cache when time allows.
2. Run a lite/medium data-quality pass for `SIVE.ST` after global routing.
3. Add Japan/Taiwan/Sweden local-provider enrichments only if yfinance leaves decision-relevant gaps.
4. Add more holdout samples before changing weights again.
5. Only then revisit whether current 25/17/28/15/15 should move toward a more quality+risk-heavy mix.
