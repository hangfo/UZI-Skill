# 美股动量真实刷新与证据契约验证（2026-07-28）

## 结论

本轮值得合回正式评分分支，但理由不是“提高了分数”，而是修复两类会污染分析过程的证据错误，同时保持评分、交易档位和纯计算性能不变：

1. US/G 股票的宏观 fetcher 不再把零搜索结果写成“中性”，也不再把中国货币政策误标为美股的利率周期；无证据时字段保持 `null` 并显式 fallback。
2. 美股短 ticker 改为边界匹配。`MU` 不再因为 `Musk` 内含 `mu` 而接收无关 Tesla 新闻；Apple/Tesla 事实核查也只拦截真实的供应链、供应商、客户、订单或合作声明，不再拦截普通横向比较。

没有改动评分公式、权重、交易阈值、技术指标、估值模型或基金路由。冻结 branch-vs-branch 为 `75 ok / 0 review / 0 possible_regression`，所有分数和交易档位变化均为零。

## 分支与边界

- baseline：`e7241dc`（正式分支起点）
- candidate：`1f5251c`（隔离分支代码检查点）
- 隔离分支：`codex/us-momentum-real-refresh-20260728`
- 未修改：`main`、`codex/windows-local-stable`、upstream
- upstream push URL 保持 `DISABLED`
- 未安装依赖、未安装 pytest、未跑 deep、未运行 update、未创建 upstream PR
- 效果结论只使用当前真实 Yahoo/生产 pipeline 数据；合成样本仅用于既有对抗边界回归，不用于宣称现实收益

## 真实样本如何选择

先用 Yahoo predefined screener 的 most-active/day-gainers 建立当日热股候选，再以 Yahoo chart v8 的真实日线检查 20/60/120 日收益、均线结构、回撤和成交金额。没有只挑选上涨样本：

- AAPL：高流动性、20/60/120 日均为正，作为成熟趋势控制组。
- AMD、MU、HOOD：60/120 日动量强，但已进入不同幅度回撤，用于检查系统是否把中期动量误当当前无风险买点。
- BMNR：当日强反弹但长期弱、深回撤，用于检查反弹诱多。
- SNDK：中期强、当前深回撤，用于和 2026-07-20 结果对照。
- SPCX：只有 30 个观察值，用于短历史 fail-closed 对抗边界。

截至 `2026-07-27` 的真实日线筛选摘要：

| 股票 | 20日 | 60日 | 120日 | 距高点 | 观察 |
|---|---:|---:|---:|---:|---|
| AAPL | +18.7% | +24.7% | +24.8% | 0.0% | 成熟上行控制组 |
| AMD | -5.1% | +46.8% | +101.0% | -14.8% | 中期强、短期回撤 |
| HOOD | -3.1% | +34.3% | +6.4% | -37.3% | 中期强但已破坏长期结构 |
| BMNR | +32.2% | -13.3% | -21.4% | -71.7% | 单段反弹对抗样本 |
| MU | -20.5% | +73.6% | +105.6% | -25.8% | 强中期动量、急跌 |
| SNDK | -38.9% | +20.1% | +92.1% | -45.3% | 高波动深回撤 |
| SPCX | -25.9% | 不足 | 不足 | 不输出 | 30 日短历史 |

## 真实生产重跑

全部使用项目 venv、默认 pipeline、`--no-resume` 和真实当前数据；lite/medium 都覆盖，没有用 mock 替换外部数据。

| 股票 | depth | 价格快照 | 投资分 | 综合分 | 档位/定调 | Stage | 客观判断 |
|---|---|---:|---:|---:|---|---|---|
| AAPL | lite | 336.91 | 67.3 | 50.2 | 观察 / 观望偏空 | 2 | 趋势最完整，但 RSI 72.1、价格在高位，不能仅凭动量追价 |
| AMD | medium | 494.95 | 56.5 | 48.0 | 谨慎观察 / 谨慎 | 2 | 长周期仍强，跌破 MA20、距高点 -14.8%，谨慎合理 |
| HOOD | medium | 95.65 | 56.0 | 50.8 | 观察 | 4 | 60 日收益强，但低于 MA20/MA200、距高点 -37.3%，Stage 4 防止追涨叙事 |
| BMNR | lite | 17.92 | 44.0 | 38.9 | 回避 | 4 | 20 日反弹无法覆盖 -71.7% 回撤和弱长期结构，护栏有效 |
| MU | medium | 900.20 | 68.6 | 52.6 | 观察 / 观望偏空 | 2 | 60/120 日很强但 20 日 -20.5%，系统没有把长期动量直接升级为买入 |
| SNDK | medium | 1278.23 | 59.5 | 47.6 | 谨慎观察 | 2 | 120 日强但 20 日 -38.9%、距高点 -45.3%，定调没有过度乐观 |
| SPCX | lite | 113.50 | 38.9 | 38.3 | 回避 | unknown | 30 个观察不足以输出 MA200/年度精度，继续 fail-closed |

`AAPL`、`MU`、`AMD` 在修复后重新走完整生产报告路径，均为 `critical=0`；唯一 warning 是 CLI 无 `agent_analysis.json`，属于项目明确允许的直跑降级。AAPL/MU 原先由普通 Tesla 提及触发的事实核查误报已消失。

报告：

- `skills/deep-analysis/scripts/reports/AAPL_20260728/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/AMD_20260728/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/MU_20260728/full-report-standalone.html`
- 同日 HOOD、BMNR、SNDK、SPCX 报告位于各自 `reports/<ticker>_20260728/`

## 与 2026-07-20 对照

| 股票 | 上次综合分 | 本次综合分 | 变化 | 档位变化 | 数据变化 |
|---|---:|---:|---:|---|---|
| MU | 52.8 | 52.6 | -0.2 | 无 | 最新日线从 07-17 更新到 07-27；短期回撤扩大 |
| SNDK | 47.6 | 47.6 | 0.0 | 无 | 最新日线更新到 07-27；仍为深回撤 |
| SPCX | 38.3 | 38.3 | 0.0 | 无 | 观察数 24→30；仍不足成熟 Stage/MA200/年度精度 |

MU 的 -0.2 是真实输入更新后的轻微变化，不是本轮代码评分漂移；同一冻结输入的 branch harness 中所有分数变化均为零。

## 事件与宏观证据验证

真实 `fetch_events.main("MU")` 返回 5 条当前 Micron 相关新闻，包括 Micron/CXMT、估值、存储芯片和 `(MU)` 标题；无关的纯 Musk/Tesla 标题已被剔除。包含 Micron 的市场综述仍保留，说明修复不是简单屏蔽 Tesla 关键词。

真实 `fetch_macro.main("Semiconductors", "U")` 当前六组搜索均无可用结果。候选输出：

- `market=U`
- `rate_market=US`
- `rate_cycle/fx_trend/geo_risk/commodity/industry_macro_impact=null`
- `fallback=true`

这比“中性（2026 货币政策）”更诚实，也避免将中国利率周期用于 US 股票。Treasury 曲线、FINRA short volume、SEC/CBOE 等补充层没有接入评分：单点收益率曲线不能直接证明联储政策方向，FINRA short volume 不是 short interest，CBOE 网络仍受授权边界限制。

## 冻结评分、对抗与性能

最终报告：

- `local-ops/state/branch-score-compare/20260728-us-momentum-real-refresh-final.md`
- `local-ops/state/us-momentum-history/20260728-us-momentum-real-refresh-final.md`

结果：

- `68 raw + 7 synthetic = 75` 个同输入样本，lite/medium 全覆盖。
- `75 ok / 0 review / 0 possible_regression`。
- investment/overall/fundamental/panel consensus 与交易档位变化均为零。
- 结构化 active P0/P1 继续约束不合理买入；伪造、已解决、过期、cross-issuer 事件继续不误伤。
- 7 只真实股票、37 个历史窗口：`37 no_change / 0 possible_regression`。
- 31 轮纯计算中位数：`0.073388s -> 0.073262s`，`performance_warning=false`。
- branch harness 正序 `2.1s -> 2.0s`，反序 candidate/baseline `2.2s/2.1s`；只判无性能回退，不宣称提速。
- 相关 direct runner `157/157`，新增/直接相关契约 `10/10`，`py_compile` 与 `git diff --check` 通过。六个顶层依赖 pytest 的文件未运行，按约束没有安装 pytest；正式起点此前完整门禁为 `269/269`。

## 公允评估与停止线

- 证据真实性：9.6/10。消除了两类可复现伪证据，效果由真实 Yahoo 新闻与真实生产 pipeline 证明。
- 回归安全：9.8/10。同输入 75 样本、37 历史窗口、交换顺序性能均无回退。
- 收益直接性：7.2/10。它提升的是研究输入可信度和误报率，不证明未来收益提升，也不应据此调高动量权重。
- 综合效果：9.2/10。属于高收益、低侵入的契约修复，建议合回正式评分分支。

剩余风险：

1. Yahoo 新闻不是 SEC 官方披露；正式事件严重度仍应依赖结构化官方 overlay。
2. 当前 US 宏观搜索覆盖率为零。正确动作是保留缺口，而不是接一个静态 Treasury 数字或“中性”默认值。
3. 公司名 token 过滤是精度优先；极短或品牌名与法人名完全不同的公司可能少收新闻，应通过真实漏召回样本扩展 alias，不应放宽成 substring。
4. AAPL 的 `buy_candidate` 是冻结纯评分交易档位，生产综合定调仍为观望偏空；两者口径不同，不能把 67.3 解读为即时买入指令。
5. 本轮没有参数调优。若未来真实前瞻命中率不能证明新增宏观源或动量参数有增益，应继续搁置。

## 下一步

合回后继续在 `codex/scoring-validation-guardrails`。常规非重叠 release 审计使用 `GPT-5.6 Terra + 中推理`；涉及评分、估值、路由、事件身份或数据契约重叠时使用 `GPT-5.6 Sol + 高推理`。下一项最有价值的工作不是调参，而是以真实漏召回样本建立 US 公司 alias/官方事件覆盖率 shadow；在覆盖率和误报率同时通过前不进入生产评分。
