# Timestamped FX and FCFF reconstruction shadow

- generated_at: `2026-07-17T09:41:10.941443+00:00`
- boundary: real observations only; no scoring, WACC, growth or production DCF mutation

- ECB official reference as-of: `2026-07-16`
- HKMA official reference as-of: `2026-06-30` (lag `17` days; reference-only)

## FX contracts

| pair | market as-of | direct | official as-of | official gap | inverse gap | triangle gap | 5-observation range | eligible | gates |
|---|---|---:|---|---:|---:|---:|---:|---|---|
| CNY/HKD | 2026-07-17 | 1.1563999652862549 | 2026-07-16 | 0.054045% | 0.225811% | 0.196475% | 0.180417% | True | - |
| CNY/USD | 2026-07-17 | 0.14778470993041992 | 2026-07-16 | 0.019265% | 4e-06% | 0.19648% | 0.190372% | True | - |
| USD/HKD | 2026-07-17 | 7.8403000831604 | 2026-07-16 | 0.018544% | 5e-06% | 0.196471% | 0.03585% | True | - |

## FCFF reconstruction

| ticker | period | currencies | partial EBIT bridge | FCF + after-tax interest | gap | gates |
|---|---|---|---:|---:|---:|---|
| 600519.SH | 2025-12-31 | CNY/CNY | 58458172833.955765 | 58415971949.84579 | 0.0722% | interest_cashflow_classification_unverified |
| 300750.SZ | 2025-12-31 | CNY/CNY | 89415913651.36996 | 93220372651.36996 | 4.0811% | interest_cashflow_classification_unverified |
| 601318.SH | 2025-12-31 | CNY/CNY | 826791630524.2739 | 668708630524.2739 | 19.1201% | financial_institution_not_applicable, fcff_methods_gap_gt_10pct, interest_cashflow_classification_unverified |
| AAPL | 2025-09-30 | USD/USD | 86263891892.50276 | None | None% | after_tax_interest_bridge_incomplete, fcff_methods_gap_gt_10pct, interest_cashflow_classification_unverified |
| AMZN | 2025-12-31 | USD/USD | -5980032185.467224 | 9522967814.532787 | 162.7959% | fcff_methods_gap_gt_10pct, nonpositive_partial_fcff, interest_cashflow_classification_unverified |
| MSTR | 2025-12-31 | USD/USD | None | None | None% | invalid_effective_tax_rate, partial_ebit_bridge_incomplete, after_tax_interest_bridge_incomplete, fcff_methods_gap_gt_10pct, interest_cashflow_classification_unverified |
| BABA | 2026-03-31 | CNY/USD | 4494964084.490723 | -43205035915.509285 | 110.4038% | fcff_methods_gap_gt_10pct, nonpositive_interest_bridge_fcff, interest_cashflow_classification_unverified, statement_quote_currency_mismatch_requires_fx |
| JPM | 2025-12-31 | USD/USD | None | -70849909580.54964 | None% | financial_institution_not_applicable, partial_ebit_bridge_incomplete, fcff_methods_gap_gt_10pct, nonpositive_interest_bridge_fcff, interest_cashflow_classification_unverified |
| 00700.HK | 2025-12-31 | CNY/HKD | 210585159275.59705 | 201324159275.59702 | 4.3977% | interest_cashflow_classification_unverified, statement_quote_currency_mismatch_requires_fx |
| 09988.HK | 2026-03-31 | CNY/HKD | 4494964084.490723 | -43205035915.509285 | 110.4038% | fcff_methods_gap_gt_10pct, nonpositive_interest_bridge_fcff, interest_cashflow_classification_unverified, statement_quote_currency_mismatch_requires_fx |
| 00005.HK | 2025-12-31 | USD/HKD | None | 73891478683.92015 | None% | financial_institution_not_applicable, partial_ebit_bridge_incomplete, fcff_methods_gap_gt_10pct, interest_cashflow_classification_unverified, statement_quote_currency_mismatch_requires_fx |

## Decision

- FX observations may be suitable for a future explicit bridge only when freshness, inverse identity, triangulation and same-date ECB cross-source agreement all pass.
- HKMA remains a second official reference, but publication lag is recorded and never hidden or used to waive freshness.
- FCFF is not promoted: provider row availability does not prove interest cash-flow classification, and method disagreement is material for several issuers.
- Static WACC, growth, tax-rate clamping and market-wide defaults remain rejected.
