# A/US/HK 时间戳 FX 与 FCFF 重建 shadow 验证

日期：2026-07-17  
隔离分支：`codex/scoring-validation-fx-fcff-shadow`  
基线：`4afce20`  
实现提交：`af59243`

## 结论先行

- **FX 契约达到 shadow-ready，但本轮不接生产。** CNY/HKD、CNY/USD、USD/HKD 同时通过 Yahoo 直连/逆向/三角恒等式、同日 ECB 独立参考汇率和时效门槛。三组同日跨源误差为 `0.054045% / 0.019265% / 0.018544%`。
- **FCFF 重建不具备生产资格。** 11 个 A/US/HK 真实样本全部保持 `production_eligible=false`。即使 600519 与 300750 两种重建只差 `0.0722% / 4.0811%`，也不能仅凭数值接近证明利息在现金流量表中的分类；AMZN、BABA/09988 则出现负值或 `>100%` 方法分歧。
- 不修改评分、交易档位、WACC、增长率、DCF、基金路由或 fetcher registry。FX 目前没有安全的生产消费者，提前接入只会增加无效参数面；FCFF 则存在明确会计语义冲突，因此两者均留在只读 shadow。

## 数据与可审计契约

### FX

- 市场源：Yahoo Finance 每日 FX close；每组都读取 direct、inverse 和两腿 triangle。
- 独立官方源：ECB 每日 EUR reference rates，以相同日期的 CNY、USD、HKD 对欧元汇率计算交叉盘，再与 Yahoo 同日 direct observation 对照。
- 第二官方参考：HKMA `er-eeri-daily`。本次接口最新为 `2026-06-30`，相对执行日滞后 17 天，因此只保留为 reference，不能豁免新鲜度门槛。
- 硬门槛：正数、市场观测不超过 3 天、官方观测不超过 3 天、inverse gap `<=0.5%`、triangle gap `<=0.75%`、同日 ECB gap `<=0.75%`。日期缺失、同日市场值缺失或任一 gap 超阈值均 fail closed。

| pair | Yahoo as-of | ECB as-of | ECB gap | inverse gap | triangle gap | 5-observation range | 结果 |
|---|---|---|---:|---:|---:|---:|---|
| CNY/HKD | 2026-07-17 | 2026-07-16 | 0.054045% | 0.098606% | 0.043385% | 0.180417% | pass |
| CNY/USD | 2026-07-17 | 2026-07-16 | 0.019265% | 0.000001% | 0.043384% | 0.166878% | pass |
| USD/HKD | 2026-07-17 | 2026-07-16 | 0.018544% | 0.000001% | 0.043384% | 0.037632% | pass |

### FCFF

比较两条互相独立但都不视为 canonical 的近似路径：

1. partial EBIT bridge：`EBIT × (1-effective tax) + D&A + signed capex + change in working capital`；它可能遗漏 D&A 以外的非现金项目。
2. after-tax-interest bridge：`provider levered FCF + interest expense × (1-effective tax)`；它依赖发行人的利息现金流分类。

有效税率仅在税前利润为正且税率落在 `0%–50%` 时使用；缺值、异常值和负值保持原样，不 clamp、不填零。金融机构直接标记不适用；财报币种与报价币种不同则要求独立 FX bridge。

| ticker | market | period | partial EBIT bridge | after-tax-interest bridge | gap | 主要 gate |
|---|---|---|---:|---:|---:|---|
| 600519.SH | A | 2025-12-31 | 584.58 亿 CNY | 584.16 亿 CNY | 0.0722% | interest classification unverified |
| 300750.SZ | A | 2025-12-31 | 894.16 亿 CNY | 932.20 亿 CNY | 4.0811% | interest classification unverified |
| 601318.SH | A | 2025-12-31 | 8267.92 亿 CNY | 6687.09 亿 CNY | 19.1201% | financial institution |
| AAPL | US | 2025-09-30 | 862.64 亿 USD | unavailable | unavailable | interest bridge incomplete |
| AMZN | US | 2025-12-31 | -59.80 亿 USD | 95.23 亿 USD | 162.7959% | sign conflict / method gap |
| MSTR | US | 2025-12-31 | unavailable | unavailable | unavailable | invalid tax / missing inputs |
| BABA | US | 2026-03-31 | 44.95 亿 CNY | -432.05 亿 CNY | 110.4038% | sign conflict / CNY-USD mismatch |
| JPM | US | 2025-12-31 | unavailable | -708.50 亿 USD | unavailable | financial institution |
| 00700.HK | HK | 2025-12-31 | 2105.85 亿 CNY | 2013.24 亿 CNY | 4.3977% | interest classification / CNY-HKD |
| 09988.HK | HK | 2026-03-31 | 44.95 亿 CNY | -432.05 亿 CNY | 110.4038% | sign conflict / CNY-HKD |
| 00005.HK | HK | 2025-12-31 | unavailable | 738.91 亿 USD | unavailable | financial institution / USD-HKD |

## 回归与性能

- direct runner：`175/175`，包括 FX 时效/逆向/三角/官方交叉源、FCFF 缺失/异常税率/永不自动晋级，以及既有评分、flow、US、overlay、fund、school、registry 契约。
- `py_compile` 与 `git diff --check` 通过；项目 venv 无 pytest，未安装新依赖。
- frozen branch compare：core + holdout + discovered cache + frozen official overlays + synthetic adversarial，lite/medium 共 `64 raw + 7 synthetic = 71`；结果 `71 ok / 0 review / 0 possible_regression`。
- investment/overall/fundamental/panel 分数最大绝对变化 `0`，交易档位变化 `0`。P0/P1 仍限制不合理买入；P2、resolved、forged、future/out-of-window 仍不误伤。
- 六轮交换顺序纯评分：正式基线 `3.0/2.9/2.7/3.3/2.7/2.6s`，中位 `2.8s`；候选 `2.4/2.9/2.7/2.6/2.3/2.4s`，中位 `2.5s`。只判定无性能回退，不宣称稳定提速。

## 吸收判断与遗留风险

- 值得吸收的是**审计工具、硬门槛、真实冻结证据和测试**，因为它们扩大可证伪面而不进入生产热路径。
- 不吸收 FCFF 数值、不新增静态 FX/WACC、不自动换汇、不新增估值输出。真正 FCFF 仍需逐发行人/准则验证利息、税、租赁和其他非现金项目的现金流分类；金融机构需要独立估值模型。
- HKMA 发布滞后必须继续可见；若 ECB 或市场源不可达/过期，未来 bridge 必须拒绝，不能回退最近常数。
- SEC Companyfacts 403、FCFE 专用折现、跨市场 WACC 与金融机构估值继续作为遗留项；在出现独立真实证据前不扩大生产面。

原始证据：`local-ops/state/fx-fcff-shadow/20260717-a-us-hk-final/`。  
分支对照：`local-ops/state/branch-score-compare/20260717-fx-fcff-shadow-final.md`。
