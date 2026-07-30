# US momentum technical-score walk-forward

- captured_at_utc: `2026-07-30T03:56:16.601007+00:00`
- source: `Yahoo Finance chart v8 adjusted daily prices`
- universe: `PATH, IREN, HURN, GRMN, MANH, AVTR`
- benchmark: `SPY`
- input_sha256: `8418eee862308f82a8021f1e78dc806614ffd719ed889a3aa31cc737d477ab93`
- signals: `724`; failures: `0`

| horizon | n | score rho net | score rho excess | top-low net | top-low excess | Stage2-4 net | Stage2-4 excess |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 21 | 487 | -0.017588 | -0.021147 | -1.2329 | -1.0962 | -2.3277 | -2.0406 |
| 63 | 159 | -0.051189 | -0.035863 | -5.1117 | -4.4005 | -5.3176 | -4.008 |
| 126 | 78 | -0.006012 | -0.000367 | -16.1549 | -16.1671 | -14.5693 | -15.7773 |

Signals use data available through the signal close, enter at the next close, and use a horizon-sized stride per issuer. Returns use Yahoo adjusted close. Net return subtracts the configured round-trip cost; excess return is gross issuer return minus SPY over the identical dates.

This validates only the historically reconstructable technical dimension. It is not a backtest of current news, entity matching, fundamentals, or the full UZI composite score.
