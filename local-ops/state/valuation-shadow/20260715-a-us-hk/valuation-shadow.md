# A/US/HK valuation shadow comparison

- generated_at: `2026-07-15T01:54:54.147754+00:00`
- evidence: live project fetchers plus yfinance HK shadow supplement
- boundary: diagnostic only; no production scoring or DCF input changes

| ticker | market | latest | 3Y median | 5Y median | latest/3Y | currencies | canonical gate |
|---|---|---:|---:|---:|---:|---|---|
| 600519.SH | A | 583.95 | 639.73 | 606.2 | 0.9128 | CNY / CNY | production_missing_debt_or_cash_bridge |
| 300750.SZ | A | 908.75 | 658.1 | 592.01 | 1.3809 | CNY / CNY | fcf_sign_instability, production_missing_debt_or_cash_bridge |
| 601318.SH | A | 6502.77 | 3757.96 | 3757.96 | 1.7304 | CNY / CNY | financial_institution_not_applicable, latest_materially_differs_from_3y_median, production_missing_debt_or_cash_bridge |
| AAPL | U | 987.67 | 995.84 | None | 0.9918 | USD / USD | production_discount_rate_contract_not_verified |
| AMZN | U | 76.95 | 322.17 | None | 0.2388 | USD / USD | fcf_sign_instability, latest_materially_differs_from_3y_median, production_discount_rate_contract_not_verified |
| MSTR | U | -225.8 | -221.39 | None | 1.0199 | USD / USD | non_positive_latest_fcf, production_discount_rate_contract_not_verified |
| JPM | U | -1477.82 | -420.12 | None | 3.5176 | USD / USD | financial_institution_not_applicable, non_positive_latest_fcf, fcf_sign_instability, latest_materially_differs_from_3y_median, production_discount_rate_contract_not_verified |
| 00700.HK | H | 1901.71 | 1745.55 | None | 1.0895 | CNY / HKD | statement_quote_currency_mismatch_requires_fx, production_missing_debt_or_cash_bridge, production_discount_rate_contract_not_verified |
| 09988.HK | H | -507.24 | 775.37 | None | -0.6542 | CNY / HKD | non_positive_latest_fcf, statement_quote_currency_mismatch_requires_fx, fcf_sign_instability, production_missing_debt_or_cash_bridge, production_discount_rate_contract_not_verified |
| 00005.HK | H | 251.05 | 354.16 | None | 0.7089 | USD / HKD | financial_institution_not_applicable, statement_quote_currency_mismatch_requires_fx, production_missing_debt_or_cash_bridge, production_discount_rate_contract_not_verified |

## Raw annual evidence

- `600519.SH`: periods=['2020', '2021', '2022', '2023', '2024', '2025']; FCF=[495.79, 606.2, 313.92, 639.73, 877.85, 583.95] CNY 亿
- `300750.SZ`: periods=['2020', '2021', '2022', '2023', '2024', '2025']; FCF=[51.28, -8.6, 129.94, 592.01, 658.1, 908.75] CNY 亿
- `601318.SH`: periods=['2020', '2021', '2022', '2023', '2024', '2025']; FCF=[3020.8, 779.3, 4679.05, 3525.93, 3757.96, 6502.77] CNY 亿
- `AAPL`: periods=['2022', '2023', '2024', '2025']; FCF=[1114.43, 995.84, 1088.07, 987.67] USD 亿
- `AMZN`: periods=['2022', '2023', '2024', '2025']; FCF=[-168.93, 322.17, 328.78, 76.95] USD 亿
- `MSTR`: periods=['2022', '2023', '2024', '2025']; FCF=[-2.87, -18.93, -221.39, -225.8] USD 亿
- `JPM`: periods=['2022', '2023', '2024', '2025']; FCF=[1071.19, 129.74, -420.12, -1477.82] USD 亿
- `00700.HK`: periods=['2022-12-31', '2023-12-31', '2024-12-31', '2025-12-31']; FCF=[952.41, 1745.55, 1624.73, 1901.71] CNY 亿
- `09988.HK`: periods=['2023-03-31', '2024-03-31', '2025-03-31', '2026-03-31']; FCF=[1654.0, 1496.64, 775.37, -507.24] CNY 亿
- `00005.HK`: periods=['2022-12-31', '2023-12-31', '2024-12-31', '2025-12-31']; FCF=[149.46, 354.16, 614.19, 251.05] USD 亿
