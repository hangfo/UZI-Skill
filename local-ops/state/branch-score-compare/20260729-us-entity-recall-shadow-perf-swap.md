# 分支评分对照 - 20260729-us-entity-recall-shadow-perf-swap

基线分支：`d4522aa`
候选分支：`48e20fc4c9fe9823ab055155511be3bc503cb78b`
生成时间：2026-07-29 11:00:37 +0800
基线耗时：`8.7s`
候选耗时：`8.5s`

## 汇总

- ok: 79
- review: 0
- possible_regression: 0

## 归因汇总

- 数据质量边界需复核 (`data_quality_uncertain`): 36
- 稳定无显著变化 (`stable_no_material_change`): 43

## 置信度汇总

- high: 40
- medium: 39

## 交叉支持汇总

- 中等交叉支持 (`moderate`): 36
- 强交叉支持 (`strong`): 43

## 可靠性汇总

- 高可靠 (`high`): 32
- 中等可靠 (`medium`): 47

## 缓存 Raw Data

| 判定 | 归因 | 置信度 | 交叉支持 | 可靠性 | 模式 | 样本 | 基线 | 候选 | 变化 | 基线秒 | 候选秒 | 基线档位 | 候选档位 | 边界余量 | 标记 |
|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---:|---|
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | lite | 600519.SH | 59.0 | 59.0 | 0.0 | 0.128 | 0.120 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | lite | 00700.HK | 59.0 | 59.0 | 0.0 | 0.014 | 0.012 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | AAPL | 67.3 | 67.3 | 0.0 | 0.015 | 0.012 | buy_candidate | buy_candidate | 7.3 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | MSTR | 34.3 | 34.3 | 0.0 | 0.011 | 0.017 | avoid | avoid | 10.7 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | AXTI | 31.9 | 31.9 | 0.0 | 0.016 | 0.013 | avoid | avoid | 13.1 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | CRCL | 33.3 | 33.3 | 0.0 | 0.012 | 0.012 | avoid | avoid | 11.7 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | SIVE.ST | 36.3 | 36.3 | 0.0 | 0.021 | 0.014 | avoid | avoid | 8.7 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | 688017.SH | 54.9 | 54.9 | 0.0 | 0.024 | 0.017 | cautious | cautious | 10.1 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | AI | 27.5 | 27.5 | 0.0 | 0.013 | 0.015 | avoid | avoid | 37.5 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | BMNR | 44.0 | 44.0 | 0.0 | 0.012 | 0.013 | cautious | cautious | 21.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | GEN | 59.0 | 59.0 | 0.0 | 0.016 | 0.010 | watch | watch | 6.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | lite | HOOD | 56.0 | 56.0 | 0.0 | 0.020 | 0.013 | watch | watch | 9.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlay_000851.SZ_negative_event | 59.9 | 59.9 | 0.0 | 0.018 | 0.013 | watch | watch | 0.1 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlaycf_000851.SZ_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.019 | 0.013 | watch | watch | 0.9 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlay_002038.SZ_negative_event | 64.4 | 64.4 | 0.0 | 0.013 | 0.008 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 中等交叉支持 | medium(71) | lite | __overlaycf_002038.SZ_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.014 | 0.013 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlay_00841.HK_negative_event | 64.4 | 64.4 | 0.0 | 0.009 | 0.009 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 中等交叉支持 | medium(71) | lite | __overlaycf_00841.HK_on_00700.HK_negative_event | 59.0 | 59.0 | 0.0 | 0.012 | 0.014 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlay_03616.HK_negative_event | 64.4 | 64.4 | 0.0 | 0.008 | 0.010 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 中等交叉支持 | medium(71) | lite | __overlaycf_03616.HK_on_00700.HK_negative_event | 59.0 | 59.0 | 0.0 | 0.012 | 0.013 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlay_601872.SH_negative_event | 64.4 | 64.4 | 0.0 | 0.009 | 0.010 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 中等交叉支持 | medium(71) | lite | __overlaycf_601872.SH_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.027 | 0.012 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlay_HUBG_negative_event | 59.9 | 59.9 | 0.0 | 0.010 | 0.009 | watch | watch | 0.1 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlaycf_HUBG_on_AAPL_negative_event | 59.9 | 59.9 | 0.0 | 0.012 | 0.012 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlay_SMCI_negative_event | 64.4 | 64.4 | 0.0 | 0.009 | 0.011 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __overlaycf_SMCI_on_AAPL_negative_event | 64.9 | 64.9 | 0.0 | 0.012 | 0.013 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(72) | 强交叉支持 | medium(60) | lite | __overlayres_SMCI_negative_event | 64.4 | 64.4 | 0.0 | 0.009 | 0.011 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(72) | 强交叉支持 | medium(60) | lite | __overlaycf_SMCI_on_AAPL_resolution | 67.3 | 67.3 | 0.0 | 0.013 | 0.013 | buy_candidate | buy_candidate | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_empty_recent_news_stale_legacy | 64.4 | 64.4 | 0.0 | 0.012 | 0.011 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __synthetic_single_strong_negative_event | 64.4 | 64.4 | 0.0 | 0.008 | 0.008 | watch | watch | 0.9 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_negated_negative_event | 64.4 | 64.4 | 0.0 | 0.010 | 0.014 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | high(80) | 中等交叉支持 | high(75) | lite | __synthetic_missing_financials_raw | 54.5 | 54.5 | 0.0 | 0.009 | 0.010 | cautious | cautious | 10.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | lite | __synthetic_verified_structured_p1 | 64.4 | 64.4 | 0.0 | 0.009 | 0.008 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_forged_structured_p1 | 64.4 | 64.4 | 0.0 | 0.010 | 0.019 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_resolved_structured_p1 | 64.4 | 64.4 | 0.0 | 0.010 | 0.009 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | lite | __synthetic_out_of_window_structured_p1 | 64.4 | 64.4 | 0.0 | 0.011 | 0.009 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | medium | 600519.SH | 59.0 | 59.0 | 0.0 | 0.014 | 0.011 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | medium | 00700.HK | 59.0 | 59.0 | 0.0 | 0.013 | 0.014 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | AAPL | 67.3 | 67.3 | 0.0 | 0.012 | 0.012 | buy_candidate | buy_candidate | 7.3 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | MSTR | 35.5 | 35.5 | 0.0 | 0.011 | 0.010 | avoid | avoid | 9.5 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | AXTI | 31.9 | 31.9 | 0.0 | 0.011 | 0.011 | avoid | avoid | 13.1 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | CRCL | 34.5 | 34.5 | 0.0 | 0.012 | 0.012 | avoid | avoid | 10.5 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | SIVE.ST | 36.3 | 36.3 | 0.0 | 0.012 | 0.010 | avoid | avoid | 8.7 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | 688017.SH | 57.8 | 57.8 | 0.0 | 0.023 | 0.021 | watch | watch | 7.2 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | AI | 27.5 | 27.5 | 0.0 | 0.011 | 0.010 | avoid | avoid | 37.5 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | BMNR | 44.0 | 44.0 | 0.0 | 0.012 | 0.011 | cautious | cautious | 21.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | GEN | 59.0 | 59.0 | 0.0 | 0.011 | 0.013 | watch | watch | 6.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | medium | HOOD | 56.0 | 56.0 | 0.0 | 0.013 | 0.011 | watch | watch | 9.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlay_000851.SZ_negative_event | 59.9 | 59.9 | 0.0 | 0.010 | 0.010 | watch | watch | 0.1 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlaycf_000851.SZ_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.013 | 0.013 | watch | watch | 0.9 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlay_002038.SZ_negative_event | 64.4 | 64.4 | 0.0 | 0.011 | 0.009 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 中等交叉支持 | medium(71) | medium | __overlaycf_002038.SZ_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.019 | 0.013 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlay_00841.HK_negative_event | 64.4 | 64.4 | 0.0 | 0.010 | 0.010 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 中等交叉支持 | medium(71) | medium | __overlaycf_00841.HK_on_00700.HK_negative_event | 59.0 | 59.0 | 0.0 | 0.015 | 0.013 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlay_03616.HK_negative_event | 64.4 | 64.4 | 0.0 | 0.012 | 0.011 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 中等交叉支持 | medium(71) | medium | __overlaycf_03616.HK_on_00700.HK_negative_event | 59.0 | 59.0 | 0.0 | 0.017 | 0.014 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlay_601872.SH_negative_event | 64.4 | 64.4 | 0.0 | 0.020 | 0.008 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | high(82) | 中等交叉支持 | medium(71) | medium | __overlaycf_601872.SH_on_600519.SH_negative_event | 59.0 | 59.0 | 0.0 | 0.013 | 0.013 | watch | watch | 1.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlay_HUBG_negative_event | 59.9 | 59.9 | 0.0 | 0.009 | 0.009 | watch | watch | 0.1 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlaycf_HUBG_on_AAPL_negative_event | 59.9 | 59.9 | 0.0 | 0.013 | 0.010 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlay_SMCI_negative_event | 64.4 | 64.4 | 0.0 | 0.010 | 0.010 | watch | watch | 0.6 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __overlaycf_SMCI_on_AAPL_negative_event | 64.9 | 64.9 | 0.0 | 0.010 | 0.011 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(72) | 强交叉支持 | medium(60) | medium | __overlayres_SMCI_negative_event | 64.4 | 64.4 | 0.0 | 0.011 | 0.009 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(72) | 强交叉支持 | medium(60) | medium | __overlaycf_SMCI_on_AAPL_resolution | 67.3 | 67.3 | 0.0 | 0.013 | 0.014 | buy_candidate | buy_candidate | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_empty_recent_news_stale_legacy | 64.4 | 64.4 | 0.0 | 0.010 | 0.013 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __synthetic_single_strong_negative_event | 64.4 | 64.4 | 0.0 | 0.009 | 0.009 | watch | watch | 0.9 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_negated_negative_event | 64.4 | 64.4 | 0.0 | 0.009 | 0.014 | watch | watch | 0.0 | - |
| ok | 数据质量边界需复核 | high(80) | 中等交叉支持 | high(75) | medium | __synthetic_missing_financials_raw | 54.5 | 54.5 | 0.0 | 0.011 | 0.011 | cautious | cautious | 10.5 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | medium | __synthetic_verified_structured_p1 | 64.4 | 64.4 | 0.0 | 0.009 | 0.015 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_forged_structured_p1 | 64.4 | 64.4 | 0.0 | 0.009 | 0.010 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_resolved_structured_p1 | 64.4 | 64.4 | 0.0 | 0.009 | 0.014 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | medium(64) | 强交叉支持 | medium(52) | medium | __synthetic_out_of_window_structured_p1 | 64.4 | 64.4 | 0.0 | 0.009 | 0.010 | watch | watch | 0.0 | - |

## Synthetic 对抗样本

| 判定 | 归因 | 置信度 | 交叉支持 | 可靠性 | 样本 | 基线 | 候选 | 变化 | 基线秒 | 候选秒 | 基线档位 | 候选档位 | 边界余量 | 标记 |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---:|---|
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | theme_only_microcap | 42.4 | 42.4 | 0.0 | 0.000 | 0.000 | cautious | cautious | 15.6 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | quality_compounder_no_momentum | 59.0 | 59.0 | 0.0 | 0.000 | 0.000 | watch | watch | 4.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | expensive_profitable_platform | 61.4 | 61.4 | 0.0 | 0.000 | 0.000 | watch | watch | 8.6 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(87) | high_quality_stage3_confirmed_downtrend | 59.0 | 59.0 | 0.0 | 0.000 | 0.000 | watch | watch | 5.0 | - |
| ok | 数据质量边界需复核 | medium(72) | 中等交叉支持 | medium(55) | stage4_missing_price_high_quality | 59.0 | 59.0 | 0.0 | 0.000 | 0.000 | watch | watch | 0.0 | - |
| ok | 稳定无显著变化 | high(90) | 强交叉支持 | high(90) | a_share_youzi_heat_institutional_selling | 33.8 | 33.8 | 0.0 | 0.000 | 0.000 | avoid | avoid | 21.2 | - |
| ok | 数据质量边界需复核 | high(90) | 中等交叉支持 | high(82) | missing_financials_theme_heat | 50.6 | 50.6 | 0.0 | 0.000 | 0.000 | cautious | cautious | 4.4 | - |

## 说明

- `review` 表示分数或档位变化值得检查，但不自动等同于回退。
- `possible_regression` 表示候选分支违反了样本特定决策边界。
- `归因` 是稳定枚举，优先按执行失败、字段契约、硬边界、样本预期和漂移强度分类。
- `置信度` 不是预测胜率，而是本次判定的证据完整度；执行错误、分数缺失、贴近边界、弱预期样本会降低置信度。
- `交叉支持` 衡量同类归因是否被不同样本来源和 lite/medium 模式共同支持；它不改变判定，只用于识别过拟合风险。
- `可靠性` 综合置信度、交叉支持和阈值敏感性；它不改变判定，只决定结论能说多满。
- `边界余量` 为候选结果距离最近预设边界的分数；负数表示越界，越接近 0 越需要人工复核。
