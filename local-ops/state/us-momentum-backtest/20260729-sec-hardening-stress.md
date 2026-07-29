# US momentum technical-score walk-forward

- captured_at_utc: `2026-07-29T09:45:40.659880+00:00`
- source: `Yahoo Finance chart v8 adjusted daily prices`
- universe: `INTC, SOFI, JBLU, AMKR, GLW, ONDS, QS, RIG`
- benchmark: `SPY`
- input_sha256: `e5889132dd0aa8b268eb4b6992d960974f7a206aa86ed055a6663f07c9e9c2d4`
- signals: `1045`; failures: `0`

| horizon | n | score rho net | score rho excess | top-low net | top-low excess | Stage2-4 net | Stage2-4 excess |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 21 | 703 | 0.021745 | 0.030524 | 0.1361 | 0.4734 | -0.3053 | -0.1148 |
| 63 | 230 | 0.019945 | 0.044436 | -2.0547 | -0.9559 | 2.4776 | 2.345 |
| 126 | 112 | 0.02439 | 0.011933 | -4.0997 | -6.1755 | 7.8016 | 4.4815 |

Signals use data available through the signal close, enter at the next close, and use a horizon-sized stride per issuer. Returns use Yahoo adjusted close. Net return subtracts the configured round-trip cost; excess return is gross issuer return minus SPY over the identical dates.

This validates only the historically reconstructable technical dimension. It is not a backtest of current news, entity matching, fundamentals, or the full UZI composite score.
