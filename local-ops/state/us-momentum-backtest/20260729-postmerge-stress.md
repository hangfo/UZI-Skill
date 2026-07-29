# US momentum technical-score walk-forward

- captured_at_utc: `2026-07-29T07:36:51.561194+00:00`
- source: `Yahoo Finance chart v8 adjusted daily prices`
- universe: `AAL, PLUG, INCY, PLTR, AMC, PATH, GLW, SNAP`
- benchmark: `SPY`
- input_sha256: `6f14a76cb2d446d67de4a93fe47d333a79a707dc6793b5335abeb60e59577d0d`
- signals: `1103`; failures: `0`

| horizon | n | score rho net | score rho excess | top-low net | top-low excess | Stage2-4 net | Stage2-4 excess |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 21 | 742 | 0.080642 | 0.084456 | 4.9247 | 4.8961 | 3.7833 | 3.4278 |
| 63 | 243 | 0.150165 | 0.165518 | 12.1093 | 12.149 | 13.7608 | 12.9583 |
| 126 | 118 | 0.203813 | 0.147253 | 8.4165 | 6.2649 | 41.3874 | 36.8918 |

Signals use data available through the signal close, enter at the next close, and use a horizon-sized stride per issuer. Returns use Yahoo adjusted close. Net return subtracts the configured round-trip cost; excess return is gross issuer return minus SPY over the identical dates.

This validates only the historically reconstructable technical dimension. It is not a backtest of current news, entity matching, fundamentals, or the full UZI composite score.
