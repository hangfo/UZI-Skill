# Report market-field and data-quality audit · 2026-08-25

## Verdict

The NVDA page exposed a real presentation and data-integrity regression, not a
scoring regression. The report treated every configured dimension as if it were
both applicable to every market and enabled by every analysis depth. As a
result, a US `lite` run reported disabled or A-share-only concepts such as
Northbound/margin financing and LHB as missing data. The banner also claimed
that browser/MX/WebSearch recovery had been attempted even when `lite` had
explicitly disabled those routes.

The repair introduces one market/depth contract shared by integrity checks,
recovery hints, report cards and stage2-only rerenders. It does not change any
score, momentum, Stage, event, valuation or trading threshold.

## Why NVDA showed the box while the older LAD page did not

The Data Quality banner is not a newly invented panel: its CSS/template existed
in the older LAD HTML. LAD's old cache had no rendered recovery artifact, so the
placeholder stayed empty. The newer pipeline consistently wrote
`_data_gaps.json`, but its integrity code counted all 20 dimensions regardless
of `market=U` and `depth=lite`. That lifecycle improvement therefore revealed a
bad applicability model and produced the 72% / 13-gap box shown in the supplied
screenshot.

After repair, the same real NVDA run has 3 unresolved, applicable fields and
81% coverage: ROE history, PE five-year percentile and PB five-year percentile.
They are legitimate US evidence gaps. The banner no longer contains
Northbound/margin financing or LHB and no longer claims recovery methods that
were not run.

## Market contract

| Dimension | A share | Hong Kong | US / other global | Current UZI action |
|---|---|---|---|---|
| Capital flow | Northbound, margin financing, shareholder count | Stock Connect eligibility and Southbound observation | Do not reuse A-share labels | A/H only; hide for US/global until a validated adapter exists |
| LHB | Applicable | Not applicable | Not applicable | A only |
| Sell-side research | Current collector is A-share oriented | Analyst estimates are a valid concept but not wired through this collector | Analyst estimates are a valid concept but not wired through this collector | Hide unsupported collector rather than relabel empty A-share output |
| Sentiment | A-share market sentiment / influencer evidence | Generic market sentiment | Generic market sentiment | Market-specific title |
| Trap scan | A-share promotion/manipulation scan | Promotion/manipulation risk | Promotion/manipulation risk | Never equate an unexecuted heavy scan with “safe” |
| Public portfolios | A-share contest/public portfolio context | Public portfolio holdings | Public portfolio holdings | Market-neutral label outside A shares |

`a-stock-data` remains an A-share supplement. Its Northbound, margin financing,
LHB and related fields must not leak into US/HK reports. `global-stock-data`
remains a US/HK supplement. SEC/FINRA/Yahoo concepts may support a future US
flow/evidence adapter, but FINRA short volume must not be presented as short
interest. CBOE remains unauthorized and unused. The skills' sample code was not
copied into UZI merely to make a box look complete.

## Page comparison

The two historical pages are not an A/B score experiment: they use different
companies, dates, caches and code generations. Layout and evidence changes can
be compared; score differences cannot be attributed to the update.

| Item | LAD 2026-07-30 | NVDA before this repair | NVDA after repair |
|---|---:|---:|---:|
| Market / profile | US / legacy profile not persisted | US / lite | US / lite persisted |
| Rendered data-gap banner | No | Yes: 13 gaps, 72% | Yes: 3 valid gaps, 81% |
| Dimension cards | 19 | 19 despite lite | 5 enabled and applicable cards |
| US report shows capital-flow/LHB cards | Yes | Yes | No |
| Unrun heavy trap scan appears safe | Yes | Yes | No: explicitly “not executed” |
| Tactical buy-zone label | Youzi | Youzi | Tactical for non-A markets |
| Currency | Legacy page contains RMB presentation for a US name | USD | USD |
| Institutional modeling | Section exists but older inputs are sparse | New DCF/comps/LBO paths were introduced | Paths remain, but unsupported US discount-rate input is evidence-gated off |

Both pages otherwise retain the same major shell: conclusion, debate, bull/bear,
panel, chat, copy-trade summary, dimension section, institutional valuation,
risks and buy zones. The newer generation adds genuine capability in global
peer/TTM evidence, institutional model components, data-gap lifecycle and USD
formatting. The regression was that those additions lacked a single market and
depth applicability contract.

## Validation

- Frozen cached scores were identical before/after the repair for NVDA 61.5,
  LAD 56.6, MU 61.3, LLY 61.8 and JNJ 61.1; every dimension score was unchanged.
- The cached regression basket passed for 600519, 00700, AAPL, MSTR and AXTI in
  lite and medium profiles with no score/tier regression.
- Fresh real-data `NVDA --depth lite --no-browser --no-resume`: overall 57.1,
  fundamental 61.5, investment 72.2, critical issues 0; 5 cards, 3 valid gaps,
  no A-share capital/LHB card.
- Fresh real-data `MU --depth lite --no-browser --no-resume`: overall 56.3,
  fundamental 61.7, investment 68.9, critical issues 0; 5 cards, 3 valid gaps,
  no A-share capital/LHB card.
- New focused contract tests: 7/7 passed. All direct-compatible files together:
  673/680 passed. The seven failures reproduce older unrelated contracts:
  three tests still expect all non-US global venues to be `G` instead of the
  current ISO-like country markets, one profile/process-isolation assertion,
  one A-share display-rounding assertion, and two Windows Bash executable/syntax
  checks. Thirteen pytest-import files remain unrun because pytest is absent and
  dependencies were not installed.
- Python compilation and diff whitespace checks passed. SEC credentials were
  not printed; CBOE requests were zero; TradingView unofficial interfaces were
  not used.

## Investment interpretation and limits

NVDA and MU remain neutral/observe outputs, despite strong investment sub-scores.
The current missing five-year valuation percentiles and unsupported US discount
rate make them unsuitable for a valuation-driven conviction upgrade. Their
cross-sectional score difference versus LAD is not return evidence. This UI and
evidence-contract repair therefore provides no basis to tune momentum, scoring
or trade thresholds, and no historical backtest parameter was optimized.

For future upstream intake, each field should move through four explicit states:
`applicable`, `enabled`, `fetched`, and `validated`. Upstream changes should be
absorbed semantically behind that contract, with frozen-input score comparison
and at least one real A/H/US render before formal integration.
