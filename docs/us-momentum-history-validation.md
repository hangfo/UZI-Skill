# 美股动量历史完整性验证（2026-07-20）

## 结论

值得吸收，而且只应吸收“证据完整性”修复，不应借机增加动量奖励或调评分阈值。旧实现只要求 60 个交易日就计算 `MA200` 并判定 Stage 1-4，还会把不足 250 日的 `pct_from_year_high` 写成 `0`。这会把新股、重组后短历史和数据截断误读成成熟趋势。候选实现改为：不足 200 日时 Stage 未知，不足各均线周期时对应 MA 为 `null`，不足 250 日时年度高低点及偏离为 `null`；同时保留实际可观察区间高低点供展示。

修复不改变评分公式、交易档位、事件 P0/P1/P2 契约、估值、基金路由或报告入口。完整历史股票继续得到原 Stage；短历史只从“伪精确”降为“未知”。

## 真实样本与方法

- 截止日：Yahoo 日线最后交易日 `2026-07-17`，抓取时间 `2026-07-20`。
- 股票：`MU/WDC/STX/SNDK/GEV/BMNR/CRCL/FIG/SPCX`，覆盖成熟半导体动量、新上市/短历史和负动量反例。
- 每只股票的真实日线只抓一次，再把完全相同的 bars 分别交给 baseline=`2fdc8b4` 与候选代码；窗口为 60/90/120/180/200/full。历史窗口是实际交易记录的截面，不是生成价格。
- 共 49 个配对：`42 beneficial_contract_fix / 7 no_change / 0 possible_regression`。

| 类别 | 真实结果 | 含义 |
|---|---:|---|
| 60-180 日窗口 | 旧版大量给出 Stage 1-4；候选全部 Stage unknown | 未拥有 MA200 时不推断长期趋势 |
| 200 日窗口 | 两版 Stage 一致；候选仍不输出完整年度偏离 | 200 日足够 Stage，不等于 250 日年度窗口 |
| 成熟 full | MU/WDC/STX/SNDK/GEV/BMNR/CRCL 的 Stage 全部不变 | 没有破坏成熟动量识别 |
| FIG full（242 日） | Stage 4 保留；年度高点偏离改为 null | 精确区分趋势证据和完整年度证据 |
| SPCX full（24 日） | Stage unknown 保留；伪 MA200/年度偏离被移除 | 新股边界 fail closed |

典型历史反事实包括：MU 120 日曾被判 Stage 2、SNDK 180 日曾被判 Stage 2、GEV 60/90/120 日均曾被判 Stage 2；这些判断都依赖不足 200 日的“MA200”，候选已拒绝。完整逐行表保存在 `local-ops/state/momentum-shadow/20260720-us-momentum-history-31run.md`。

## 生产入口真实运行

使用项目 venv、`--no-resume` 和生产 pipeline 重新抓取，没有 mock、没有 deep、没有安装依赖：

| 股票 | 深度 | 最新 K 线 | 观察数 | Stage / MA200 | 年度窗口 | 综合结论 |
|---|---|---|---:|---|---|---|
| MU | lite | 2026-07-17 | 501 | Stage 2 / 482.91 | 完整，距高点 -30.03% | 52.8，观望偏空 |
| SNDK | medium | 2026-07-17 | 357 | Stage 2 / 781.73 | 完整，距高点 -41.98% | 47.6，谨慎 |
| SPCX | lite | 2026-07-17 | 24 | unknown / null | 不完整，偏离 null | 38.3，谨慎 |

MU lite 的 7 个启用 fetcher 用时约 5.5 秒，SNDK medium 的 20 个 fetcher 用时约 7.1 秒，SPCX lite 约 3.1 秒；均无 traceback。当前环境没有 `MX_APIKEY`，美股宏观、行业、材料、期货和政策等通用补充维度仍有数据缺口，所以这些综合分只证明生产链路与边界行为，不作为投资收益预测。

报告：

- `skills/deep-analysis/scripts/reports/MU_20260720/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/SNDK_20260720/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/SPCX_20260720/full-report-standalone.html`

## 冻结评分、对抗与性能

- core + holdout + discovered cache + 真实冻结 overlays + synthetic adversarial，lite/medium 共 `64 raw + 7 synthetic = 71`：`71 ok / 0 review / 0 possible_regression`。
- 所有投资评分变化 `0`，所有交易档位变化 `0`。结构化 active P0/P1 继续被消费；P2、伪造、已解决和过期记录继续不误伤。
- 31 轮纯技术指标计算中位数：baseline `0.092015s`，candidate `0.087824s`，约 `-4.6%`；进程总时 `4.454s -> 4.130s`，无性能告警。首次 9 轮曾出现方向相反的小样本噪声，因此没有采用单次结果。
- direct runner `213/213`，另有 `py_compile` 和 `git diff --check` 通过。

## 剩余风险与停止线

- Yahoo/行情源可能发生复权或历史修订；影子工具保留抓取时间和同一输入对照，但不是交易所官方审计数据。
- 200/250 是指标定义所需的最小观察数，不是收益优化参数；不要围绕本篮子调整阈值。
- 不新增“热门动量加分”。动量强不等于估值合理、基本面充分或事件安全；本轮 SNDK 就是强中期动量但综合仍谨慎的真实反例。
- 宏观/行业等网络缺口继续显式保留，不能用默认值填满。
- FCFF 产品化、静态 FX/WACC、基金全量枚举和新的事件关键词仍按既有停止线搁置，本修复没有为它们提供新证据。

## 建议

全部硬门槛通过，建议 fast-forward 合回 `codex/scoring-validation-guardrails`，后续继续在该正式评分分支开发；不要合入 `main` 或 `codex/windows-local-stable`。效果评分 `9.3/10`：收益来自消除真实新股伪精确且不改变成熟样本和交易决策；扣分来自行情源非交易所官方、生产通用维度仍有网络缺口。
