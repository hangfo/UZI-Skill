# US momentum technical-score walk-forward

- captured_at_utc: `2026-07-30T04:36:17.811234+00:00`
- source: `Yahoo Finance chart v8 adjusted daily prices`
- universe: `LAD, EXLS, CBZ, GEHC, VRT, HIMS`
- benchmark: `SPY`
- input_sha256: `8b7f9825f112154082d8532a45b1b45f7f8264a826ab81a162755f2271b82969`
- signals: `750`; failures: `0`

| horizon | n | score rho net | score rho excess | top-low net | top-low excess | Stage2-4 net | Stage2-4 excess |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 21 | 505 | -0.040638 | 0.004855 | -2.0551 | -1.5006 | 0.5834 | 0.814 |
| 63 | 165 | -0.078447 | -0.052077 | -7.4095 | -5.4703 | -2.2108 | -1.096 |
| 126 | 80 | -0.116066 | -0.125176 | -10.1289 | -10.4948 | 4.3094 | 0.9587 |

Signals use data available through the signal close, enter at the next close, and use a horizon-sized stride per issuer. Returns use Yahoo adjusted close. Net return subtracts the configured round-trip cost; excess return is gross issuer return minus SPY over the identical dates.

This validates only the historically reconstructable technical dimension. It is not a backtest of current news, entity matching, fundamentals, or the full UZI composite score.
