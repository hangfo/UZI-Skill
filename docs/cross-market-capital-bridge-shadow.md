# A/US/HK 资本桥与现金流口径 Shadow 验证

日期：2026-07-17

## 结论

本轮不应把新的 FX、WACC 或多年归一化参数接入生产估值。真实数据证明，当前可稳定取得的 `CFO-capex` 与 Yahoo `Free Cash Flow` 都是杠杆后现金流代理，并非可直接进入企业价值 DCF 的 FCFF。若继续用它们折现为企业价值后再扣净债务，会重复计入融资影响。

因此生产修复采用最小且安全的方案：

- 将上述输入显式标为 `levered_cash_flow_proxy`。
- 现有企业价值 DCF 只接受明确的 `fcff`；其他类别返回 `unsupported_cash_flow_class_for_enterprise_dcf`。
- 美股债务和现金不再把缺失值静默写成 0；只消费资产负债表中同一期、带来源字段和财报币种的记录。
- 美股现金流币种使用 `financialCurrency`，不再错误使用交易 `currency`。真实 BABA 验证为财报 CNY、报价 USD。
- Shadow 继续保留跨源差异，但不自动选择“更好看”的值写回生产。

## 真实数据方法

标的固定为 10 个：A 股 `600519.SH/300750.SZ/601318.SH`，美股 `AAPL/AMZN/MSTR/JPM`，港股 `00700.HK/09988.HK/00005.HK`。金融机构仅验证路由和数据契约，不应用工业企业净债务 DCF。

来源与口径：

- A 股：Yahoo 财务三表对新浪资产负债表；AkShare 财务摘要中的供应商定义 FCFF/FCFE 每股值只作旁证。
- 美股：Yahoo 对东财标准化美股三表；同时尝试 SEC Companyfacts。当前网络对 SEC 返回 403，失败被显式记录，未用估算值替代。
- 港股：Yahoo 对东财标准化港股三表。
- 现金严格口径与“现金+短投/存款”分开；租赁、票据和贷款保留组件，不把不同定义强行对齐。
- 期间必须一致；差异超过 10% 只标记 `definition_or_period_gap`，不主观归因。

可复现产物：

- `local-ops/state/capital-bridge-shadow/20260717-a-us-hk-final/capital-bridge-shadow.json`
- `local-ops/state/capital-bridge-shadow/20260717-a-us-hk-final/capital-bridge-shadow.md`
- `local-ops/state/valuation-shadow/20260717-balance-sheet-fx-final/valuation-shadow.json`
- `local-ops/state/valuation-shadow/20260717-balance-sheet-fx-final/valuation-shadow.md`

## 跨源结果

下表差异为 `abs(A-B)/max(abs(A),abs(B))`。空值表示定义或数据不足，绝不补 0。

| 标的 | 债务差异 | 严格现金差异 | FCF 代理差异 | 解释 |
|---|---:|---:|---:|---|
| 600519.SH | 0.00% | 0.00% | — | 两源同为 2025 年报；供应商 FCFF/FCFE 总额与 CFO-capex 仍差 23.75% |
| 300750.SZ | 0.00% | 0.00% | — | 资产负债桥一致；供应商 FCFF/FCFE 与 CFO-capex 分别差 80.76%/93.42% |
| 601318.SH | 83.11% | 26.80% | — | 保险公司口径不适用工业净债务桥；供应商 FCFF/FCFE 缺失 |
| AAPL | 8.09% | 0.00% | 0.00% | 现金流两源完全一致；债务组件范围略有差异 |
| AMZN | 19.04% | 0.00% | 0.00% | FCF 一致；债务是否含资本租赁导致范围差异 |
| MSTR | 0.06% | 0.00% | 99.50% | 东财“购买固定资产”未覆盖 Yahoo FCF 所含的大额资产/数字资产支出范围 |
| JPM | 0.00% | 93.67% | — | 银行现金与借款口径不可按工业企业解释 |
| 00700.HK | 2.59% | 0.00% | 11.78% | 严格现金一致；资本开支组件范围略超 10%；财报 CNY/报价 HKD |
| 09988.HK | 7.71% | 0.00% | 1.72% | 三项均接近；财报 CNY/报价 HKD，仍需带时间戳 FX |
| 00005.HK | 63.44% | 81.97% | 87.39% | 银行口径不适用；财报 USD/报价 HKD |

真实生产 fetcher 复验：

- AAPL：FCF `987.67 亿 USD`，债务 `986.57 亿`、广义现金 `546.97 亿`，均为 `2025-09-30`，桥接来源和期间完整。
- BABA：FCF `-507.24 亿 CNY`，债务 `2817.22 亿`、广义现金 `3168.94 亿`，均为 `2026-03-31`；修复后不再把现金流错标 USD。
- MSTR：FCF `-225.80 亿 USD`，债务 `82.36 亿`、广义现金 `23.01 亿`，均为 `2025-12-31`；负值保持为负。

## 评分与交易决策门禁

baseline=`3af25a3`，candidate=`ac4e1ad`。同一批冻结输入覆盖 core、holdout、discovered cache、官方事件 overlays、synthetic raw 和 synthetic feature，lite/medium 均运行：

- `64 raw + 7 synthetic = 71` 个配对结论。
- `71 ok / 0 review / 0 possible_regression`。
- 71 个评分变化全部为 `0`，档位变化全部为 `0`。
- P0/P1 仍阻止不合理买入；resolved、forged、out-of-window、P2/否定语境仍不误伤。
- 正式报告：`local-ops/state/branch-score-compare/20260717-capital-bridge-fcff-final.md`。

纯评分三轮交换顺序耗时：正式基线 `3.727/2.400/2.200s`，候选 `3.093/2.300/2.000s`；中位数 `2.400s -> 2.300s`。只判定无性能回退，不宣称稳定提速。真实 10 标的跨源采集合计 `76.757s`，属于独立 shadow 工具，不在生产评分热路径。

## 暂缓与剩余风险

- **FX 暂缓**：HK 财报/报价币种错配真实存在，但生产需要估值时点、来源、方向、直接/逆向交叉检查和 stale gate。只接一个当前汇率会制造新的伪精确。
- **WACC 暂缓**：静态跨市场无风险利率、ERP、税率和 beta 很快过期；在没有带日期、市场和来源的参数契约前继续 fail-closed。
- **FCFE 路径暂缓**：可另建成本权益折现且不扣净债务的模型，但必须先验证供应商 FCFE 定义。宁德时代 93.42% 的差异说明不能仅凭字段名接入。
- **SEC 复验待网络恢复**：当前主机访问 SEC Companyfacts 为 403；美股交叉验证临时使用 Yahoo+东财，不能宣称完成官方源三角验证。
- **金融机构专用估值缺口**：601318/JPM/00005 需要银行/保险专用资本和分红模型，不应复用工业企业 DCF。
- **MSTR 资产支出分类**：两源 FCF 差 99.50%，必须单独识别数字资产购置范围；不得用通用 capex 规则修补。

下一步只在独立分支做两个高价值方向：一是带时间戳和双向交叉的 FX shadow；二是从明确税后经营利润与再投资重建真正 FCFF，并与官方报表脚注核验。不要先调 WACC、增长率或评分权重。
