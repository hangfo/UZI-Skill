# Upstream intake swapped-order performance gate

Date: 2026-07-28  
Baseline: `6b295bd`  
Candidate: `5cb1323`

Each observation is the complete 64-raw + 7-synthetic, lite/medium branch
comparison.  Order was swapped so neither ref always paid first-run cost.

| run | first ref | first seconds | second ref | second seconds |
|---:|---|---:|---|---:|
| 1 | baseline | 2.3 | candidate | 2.2 |
| 2 | candidate | 4.6 | baseline | 2.6 |
| 3 | baseline | 4.1 | candidate | 2.3 |

- baseline median: `2.6s` (range `2.3–4.1s`)
- candidate median: `2.3s` (range `2.2–4.6s`)
- verdict: no performance regression

The wide process-level range is Windows startup/cache noise.  The change does
not touch pure scoring code, so these observations support only a no-regression
claim, not a speedup claim.
