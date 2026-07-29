# 分支评分对照 - 20260729-us-entity-merge-backtest-final

基线分支：`48e20fc4c9fe9823ab055155511be3bc503cb78b`
候选分支：`HEAD`
生成时间：2026-07-29 13:28:44 +0800
基线耗时：`7.9s`
候选耗时：`7.3s`

## 汇总

- ok: 93
- review: 0
- possible_regression: 0

## 归因汇总

- 数据质量边界需复核 (`data_quality_uncertain`): 40
- 稳定无显著变化 (`stable_no_material_change`): 53

## 置信度汇总

- high: 54
- medium: 39

## 交叉支持汇总

- 强交叉支持 (`strong`): 93

## 可靠性汇总

- 高可靠 (`high`): 54
- 中等可靠 (`medium`): 39

## 缓存 Raw Data

| 判定 | 归因 | 置信度 | 交叉支持 | 可靠性 | 模式 | 样本 | 基线 | 候选 | 变化 | 基线秒 | 候选秒 | 基线档位 | 候选档位 | 边界余量 | 标记 |
|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---:|---|
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | lite | 600519.SH | 59.0 | 59.0 | 0.0 | 0.112 | 0.057 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | lite | 00700.HK | 59.0 | 59.0 | 0.0 | 0.011 | 0.009 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | AAPL | 67.3 | 67.3 | 0.0 | 0.010 | 0.011 | buy_candidate | buy_candidate | 7.3 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | MSTR | 35.1 | 35.1 | 0.0 | 0.022 | 0.010 | avoid | avoid | 9.9 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | AXTI | 31.9 | 31.9 | 0.0 | 0.083 | 0.009 | avoid | avoid | 13.1 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | CRCL | 33.3 | 33.3 | 0.0 | 0.019 | 0.017 | avoid | avoid | 11.7 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | SIVE.ST | 36.3 | 36.3 | 0.0 | 0.106 | 0.016 | avoid | avoid | 8.7 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | 688017.SH | 54.9 | 54.9 | 0.0 | 0.033 | 0.013 | cautious | cautious | 10.1 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(82) | lite | LCID | 31.2 | 31.2 | 0.0 | 0.012 | 0.008 | avoid | avoid | - | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(82) | lite | CLS | 64.5 | 64.5 | 0.0 | 0.026 | 0.008 | watch | watch | - | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | AI | 27.5 | 27.5 | 0.0 | 0.019 | 0.023 | avoid | avoid | 37.5 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | BMNR | 44.0 | 44.0 | 0.0 | 0.013 | 0.009 | cautious | cautious | 21.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | FOUR | 44.2 | 44.2 | 0.0 | 0.013 | 0.013 | cautious | cautious | 20.8 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | GEN | 59.0 | 59.0 | 0.0 | 0.015 | 0.025 | watch | watch | 6.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | HOOD | 56.0 | 56.0 | 0.0 | 0.013 | 0.016 | watch | watch | 9.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | ITRI | 59.0 | 59.0 | 0.0 | 0.027 | 0.012 | watch | watch | 6.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | MARA | 35.7 | 35.7 | 0.0 | 0.021 | 0.009 | avoid | avoid | 29.3 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | NU | 59.0 | 59.0 | 0.0 | 0.014 | 0.011 | watch | watch | 6.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | T | 59.0 | 59.0 | 0.0 | 0.017 | 0.009 | watch | watch | 6.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlay_000851.SZ_negative_event | 59.9 | 59.9 | 0.0 | 0.018 | 0.008 | watch | watch | 0.1 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlaycf_000851.SZ_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.014 | 0.011 | watch | watch | 0.9 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlay_002038.SZ_negative_event | 64.4 | 64.4 | 0.0 | 0.055 | 0.007 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(76) | lite | __overlaycf_002038.SZ_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.020 | 0.019 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlay_00841.HK_negative_event | 64.4 | 64.4 | 0.0 | 0.013 | 0.011 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(76) | lite | __overlaycf_00841.HK_on_00700.HK_negative_event | 59.0 | 59.0 | 0.0 | 0.019 | 0.011 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlay_03616.HK_negative_event | 64.4 | 64.4 | 0.0 | 0.012 | 0.010 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(76) | lite | __overlaycf_03616.HK_on_00700.HK_negative_event | 59.0 | 59.0 | 0.0 | 0.020 | 0.010 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlay_601872.SH_negative_event | 64.4 | 64.4 | 0.0 | 0.064 | 0.012 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(76) | lite | __overlaycf_601872.SH_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.019 | 0.012 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlay_HUBG_negative_event | 59.9 | 59.9 | 0.0 | 0.011 | 0.010 | watch | watch | 0.1 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlaycf_HUBG_on_AAPL_negative_event | 59.9 | 59.9 | 0.0 | 0.015 | 0.022 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlay_SMCI_negative_event | 64.4 | 64.4 | 0.0 | 0.011 | 0.010 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __overlaycf_SMCI_on_AAPL_negative_event | 64.9 | 64.9 | 0.0 | 0.027 | 0.012 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(72) | 强交叉支持 | medium(60) | lite | __overlayres_SMCI_negative_event | 64.4 | 64.4 | 0.0 | 0.050 | 0.011 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(72) | 强交叉支持 | medium(60) | lite | __overlaycf_SMCI_on_AAPL_resolution | 67.3 | 67.3 | 0.0 | 0.019 | 0.028 | buy_candidate | buy_candidate | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_empty_recent_news_stale_legacy | 64.4 | 64.4 | 0.0 | 0.055 | 0.046 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __synthetic_single_strong_negative_event | 64.4 | 64.4 | 0.0 | 0.044 | 0.035 | watch | watch | 0.9 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_negated_negative_event | 64.4 | 64.4 | 0.0 | 0.066 | 0.016 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | high(80) | 强交叉支持 | high(80) | lite | __synthetic_missing_financials_raw | 54.5 | 54.5 | 0.0 | 0.076 | 0.009 | cautious | cautious | 10.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | lite | __synthetic_verified_structured_p1 | 64.4 | 64.4 | 0.0 | 0.018 | 0.008 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_forged_structured_p1 | 64.4 | 64.4 | 0.0 | 0.022 | 0.024 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_resolved_structured_p1 | 64.4 | 64.4 | 0.0 | 0.120 | 0.029 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_out_of_window_structured_p1 | 64.4 | 64.4 | 0.0 | 0.026 | 0.024 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | medium | 600519.SH | 59.0 | 59.0 | 0.0 | 0.018 | 0.044 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | medium | 00700.HK | 59.0 | 59.0 | 0.0 | 0.074 | 0.026 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | AAPL | 67.3 | 67.3 | 0.0 | 0.077 | 0.020 | buy_candidate | buy_candidate | 7.3 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | MSTR | 36.3 | 36.3 | 0.0 | 0.068 | 0.017 | avoid | avoid | 8.7 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | AXTI | 31.9 | 31.9 | 0.0 | 0.013 | 0.052 | avoid | avoid | 13.1 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | CRCL | 34.5 | 34.5 | 0.0 | 0.017 | 0.042 | avoid | avoid | 10.5 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | SIVE.ST | 36.3 | 36.3 | 0.0 | 0.014 | 0.017 | avoid | avoid | 8.7 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | 688017.SH | 57.8 | 57.8 | 0.0 | 0.036 | 0.030 | watch | watch | 7.2 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(82) | medium | LCID | 31.2 | 31.2 | 0.0 | 0.019 | 0.027 | avoid | avoid | - | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(82) | medium | CLS | 65.7 | 65.7 | 0.0 | 0.017 | 0.016 | buy_candidate | buy_candidate | - | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | AI | 27.5 | 27.5 | 0.0 | 0.019 | 0.014 | avoid | avoid | 37.5 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | BMNR | 44.0 | 44.0 | 0.0 | 0.022 | 0.014 | cautious | cautious | 21.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | FOUR | 44.2 | 44.2 | 0.0 | 0.034 | 0.030 | cautious | cautious | 20.8 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | GEN | 59.0 | 59.0 | 0.0 | 0.025 | 0.010 | watch | watch | 6.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | HOOD | 56.0 | 56.0 | 0.0 | 0.019 | 0.013 | watch | watch | 9.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | ITRI | 59.0 | 59.0 | 0.0 | 0.020 | 0.013 | watch | watch | 6.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | MARA | 36.9 | 36.9 | 0.0 | 0.017 | 0.017 | avoid | avoid | 28.1 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | NU | 59.0 | 59.0 | 0.0 | 0.014 | 0.014 | watch | watch | 6.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | T | 59.0 | 59.0 | 0.0 | 0.017 | 0.013 | watch | watch | 6.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlay_000851.SZ_negative_event | 59.9 | 59.9 | 0.0 | 0.016 | 0.013 | watch | watch | 0.1 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlaycf_000851.SZ_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.021 | 0.016 | watch | watch | 0.9 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlay_002038.SZ_negative_event | 64.4 | 64.4 | 0.0 | 0.016 | 0.010 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(76) | medium | __overlaycf_002038.SZ_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.017 | 0.013 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlay_00841.HK_negative_event | 64.4 | 64.4 | 0.0 | 0.011 | 0.010 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(76) | medium | __overlaycf_00841.HK_on_00700.HK_negative_event | 59.0 | 59.0 | 0.0 | 0.025 | 0.015 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlay_03616.HK_negative_event | 64.4 | 64.4 | 0.0 | 0.015 | 0.015 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(76) | medium | __overlaycf_03616.HK_on_00700.HK_negative_event | 59.0 | 59.0 | 0.0 | 0.014 | 0.015 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlay_601872.SH_negative_event | 64.4 | 64.4 | 0.0 | 0.023 | 0.013 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 强交叉支持 | high(76) | medium | __overlaycf_601872.SH_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.018 | 0.016 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlay_HUBG_negative_event | 59.9 | 59.9 | 0.0 | 0.013 | 0.013 | watch | watch | 0.1 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlaycf_HUBG_on_AAPL_negative_event | 59.9 | 59.9 | 0.0 | 0.015 | 0.013 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlay_SMCI_negative_event | 64.4 | 64.4 | 0.0 | 0.009 | 0.009 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __overlaycf_SMCI_on_AAPL_negative_event | 64.9 | 64.9 | 0.0 | 0.024 | 0.010 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(72) | 强交叉支持 | medium(60) | medium | __overlayres_SMCI_negative_event | 64.4 | 64.4 | 0.0 | 0.030 | 0.009 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(72) | 强交叉支持 | medium(60) | medium | __overlaycf_SMCI_on_AAPL_resolution | 67.3 | 67.3 | 0.0 | 0.016 | 0.010 | buy_candidate | buy_candidate | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_empty_recent_news_stale_legacy | 64.4 | 64.4 | 0.0 | 0.026 | 0.010 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __synthetic_single_strong_negative_event | 64.4 | 64.4 | 0.0 | 0.022 | 0.014 | watch | watch | 0.9 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_negated_negative_event | 64.4 | 64.4 | 0.0 | 0.015 | 0.013 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | high(80) | 强交叉支持 | high(80) | medium | __synthetic_missing_financials_raw | 54.5 | 54.5 | 0.0 | 0.049 | 0.013 | cautious | cautious | 10.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | medium | __synthetic_verified_structured_p1 | 64.4 | 64.4 | 0.0 | 0.034 | 0.009 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_forged_structured_p1 | 64.4 | 64.4 | 0.0 | 0.016 | 0.010 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_resolved_structured_p1 | 64.4 | 64.4 | 0.0 | 0.064 | 0.008 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_out_of_window_structured_p1 | 64.4 | 64.4 | 0.0 | 0.018 | 0.009 | watch | watch | 0.0 | - |

## Synthetic 对抗样本

| 判定 | 归因 | 置信度 | 交叉支持 | 可靠性 | 样本 | 基线 | 候选 | 变化 | 基线秒 | 候选秒 | 基线档位 | 候选档位 | 边界余量 | 标记 |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---:|---|
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | theme_only_microcap | 42.4 | 42.4 | 0.0 | 0.000 | 0.000 | cautious | cautious | 15.6 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | quality_compounder_no_momentum | 59.0 | 59.0 | 0.0 | 0.002 | 0.000 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | expensive_profitable_platform | 61.4 | 61.4 | 0.0 | 0.000 | 0.000 | watch | watch | 8.6 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | high_quality_stage3_confirmed_downtrend | 59.0 | 59.0 | 0.0 | 0.000 | 0.000 | watch | watch | 5.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 强交叉支持 | medium(60) | stage4_missing_price_high_quality | 59.0 | 59.0 | 0.0 | 0.000 | 0.000 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | a_share_youzi_heat_institutional_selling | 33.8 | 33.8 | 0.0 | 0.000 | 0.000 | avoid | avoid | 21.2 | - |
| ok | 数据质量边界需复核 | high(90) | 强交叉支持 | high(87) | missing_financials_theme_heat | 50.6 | 50.6 | 0.0 | 0.000 | 0.000 | cautious | cautious | 4.4 | - |

## 说明

- `review` 表示分数或档位变化值得检查，但不自动等同于回退。
- `possible_regression` 表示候选分支违反了样本特定决策边界。
- `归因` 是稳定枚举，优先按执行失败、字段契约、硬边界、样本预期和漂移强度分类。
- `置信度` 不是预测胜率，而是本次判定的证据完整度；执行错误、分数缺失、贴近边界、弱预期样本会降低置信度。
- `交叉支持` 衡量同类归因是否被不同样本来源和 lite/medium 模式共同支持；它不改变判定，只用于识别过拟合风险。
- `可靠性` 综合置信度、交叉支持和阈值敏感性；它不改变判定，只决定结论能说多满。
- `边界余量` 为候选结果距离最近预设边界的分数；负数表示越界，越接近 0 越需要人工复核。
