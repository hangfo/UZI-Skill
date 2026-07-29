# US momentum technical-score walk-forward

- captured_at_utc: `2026-07-29T05:17:10.418714+00:00`
- source: `Yahoo Finance chart v8 adjusted daily prices`
- universe: `AAPL, AMD, HOOD, BMNR, MU, SNDK, KNSA, OSCR, IQV, ITRI, LCID, NVDA, MSTR, NU, MARA, T, SOFI, JBLU, INTC, NOK, FOUR, CLS, RGEN, WDC, STX, GEV, CRCL, AI, GEN, ON, IT, CAT, META, GOOGL, F, PLTR, COIN`
- benchmark: `SPY`
- input_sha256: `2fe57fe0ab7613d680fce462b73980e767df75f1b27763b715b3c2dbfe527bf5`
- signals: `4518`; failures: `0`

| horizon | n | score rho net | score rho excess | top-low net | top-low excess | Stage2-4 net | Stage2-4 excess |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 21 | 3040 | 0.01551 | 0.025084 | 0.6031 | 0.7687 | 1.0469 | 1.1935 |
| 63 | 995 | 0.034393 | 0.042055 | 2.3024 | 2.5168 | 7.4894 | 7.0005 |
| 126 | 483 | 0.068719 | 0.05764 | -4.1894 | -5.0756 | 9.6122 | 7.01 |

Signals use data available through the signal close, enter at the next close, and use a horizon-sized stride per issuer. Returns use Yahoo adjusted close. Net return subtracts the configured round-trip cost; excess return is gross issuer return minus SPY over the identical dates.

This validates only the historically reconstructable technical dimension. It is not a backtest of current news, entity matching, fundamentals, or the full UZI composite score.
