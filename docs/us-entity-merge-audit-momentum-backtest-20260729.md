# US entity 合并审计与动量收益回测（2026-07-29）

## 公允结论

实体匹配候选值得吸收，但本轮仍不自动合回正式分支。三批真实 Yahoo 冻结集共 349 行：

| 数据集 | baseline precision / recall / 污染率 | candidate precision / recall / 污染率 |
|---|---|---|
| 初始命名难例，119 行 | 89.47% / 87.93% / 10.53% | 100% / 98.28% / 0 |
| 独立热门股，80 行 | 97.73% / 97.73% / 2.27% | 100% / 100% / 0 |
| 短 ticker 邻近发行人，150 行 | 86.67% / 100% / 12.82% | 100% / 100% / 0 |
| 行级合计（集合间有重叠） | TP 159 / FP 17 / FN 8；90.34% / 95.21% / 9.66% | TP 166 / FP 0 / FN 1；100% / 99.40% / 0 |

唯一候选 FN 是 `Markets brace for Fed decision and Big Tech earnings`。正文日程包含 Meta，但可见标题没有 Meta、ticker、品牌或发行人主语；Yahoo `relatedTickers` 不能单独构成发行人事件证据。它更接近 ambiguous，而不是应靠宽匹配恢复的稳定漏召回。

真实价格 walk-forward 对“提高技术/动量权重”给出否定证据：完整技术维度分数与未来超额收益 Spearman 仅 `0.025/0.042/0.058`，高分组相对低分组的平均 SPY 超额差为 `+0.77/+2.52/-5.08` 个百分点（21/63/126 日），不单调，且 126 日反向。不得据此增加动量奖励或改评分。

Stage 2 相对 Stage 4 在全样本方向较好，但跨时期并不完全稳定，只支持继续作为风险/趋势护栏，不支持升级为单独买入规则。

## alias 来源与发行人绑定规则

1. 只接受发行人官方 IR/官网明确给出的法人名、证券 ticker、完整前法人名或受控品牌。
2. alias 必须绑定单一发行人；短 ticker、常见词 ticker 不能裸匹配。
3. ticker 只在括号、交易所、`ticker/symbol/shares/stock` 等证券语境中可信。
4. 前法人名必须完整匹配；不接受普通词 `Strategy`，不接受创始人/CEO 姓名替代发行人。
5. partner/supplier/customer/former executive/deal counterparty 是关系描述，不自动把另一发行人的事件归给目标公司。
6. `relatedTickers` 只作检索线索，不能单独决定标签。

主要绑定来自发行人官网或 IR：`C3.ai`、`onsemi`、`Gartner`、`Alphabet/Google`、`Meta Platforms`、`Robinhood`、`Citi`、`Cash App`、`Norton/MoneyLion`；`MicroStrategy` 只作为 Strategy 的完整前法人名；`Nu Holdings/Nubank` 来自 Nu 官方 IR/官网；`AT&T` 来自 AT&T 官方 IR 对 NYSE ticker `T` 的绑定。

没有把 MARA 前法人名、FOUR 普通词、Saylor/CEO/创始人姓名加入生产 alias，因为独立真实集没有证明稳定 FN，污染面却更大。

## false positive / false negative 摘要

baseline 的 17 个 FP：

- `AI -> BigBear.ai` 1 条；`ON -> TXN` 1 条；`IT -> Gartner` 供应商稿 4 条。
- `NVDA -> SK Hynix` 关系反向归因 1 条。
- `NU -> Nu Skin` 4 条；`T -> T. Rowe Price` 6 条。

候选 FP 为 0。

baseline 的 8 个 FN 为 Citi 完整产品事件、onsemi 篮子中的显式 ticker、Cash App、Norton 2 条、MoneyLion、MicroStrategy 前法人名和 1 条泛 Big Tech/META 日程。候选恢复前 7 类，剩余泛标题继续 fail-closed。候选没有重新引入 MU/Musk、常见词 ticker、supplier/partner、former executive 或反向交易对手污染。

## 真实收益 walk-forward

新增只读研究工具 `tools/us_momentum_walkforward.py`，不接入生产评分。冻结数据为 Yahoo chart v8 真实复权日线：

- 37 只美股：`AAPL/AMD/HOOD/BMNR/MU/SNDK/KNSA/OSCR/IQV/ITRI/LCID/NVDA/MSTR/NU/MARA/T/SOFI/JBLU/INTC/NOK/FOUR/CLS/RGEN/WDC/STX/GEV/CRCL/AI/GEN/ON/IT/CAT/META/GOOGL/F/PLTR/COIN`
- 基准 SPY；10 年请求；实际信号日 `2017-08-09` 至 `2026-06-23`。
- 4518 个非重叠 issuer-horizon 信号：21 日 3040、63 日 995、126 日 483。
- 信号只看收盘日及以前数据；下一交易日收盘入场；每发行人按持有期抽样。
- 净收益扣 20bp 往返摩擦；比较相同日期 SPY；复权价处理拆股/分红。
- 只重建可点时还原的技术维度，不把当前新闻、alias、财务或完整综合评分倒灌历史。

冻结输入：

- `local-ops/state/us-momentum-backtest/20260729-real-adjusted-prices.json`
- SHA256 `2fe57fe0ab7613d680fce462b73980e767df75f1b27763b715b3c2dbfe527bf5`
- `local-ops/state/us-momentum-backtest/20260729-walkforward-final.json`
- `local-ops/state/us-momentum-backtest/20260729-walkforward-final.md`

### 全样本

| 前瞻期 | 技术分数 vs SPY 超额 Spearman | 高分-低分平均超额 | Stage 2-4 平均超额 | Stage 2-4 中位超额 |
|---:|---:|---:|---:|---:|
| 21 日 | 0.025 | +0.77% | +1.19% | +0.19% |
| 63 日 | 0.042 | +2.52% | +7.00% | +3.19% |
| 126 日 | 0.058 | -5.08% | +7.01% | +6.27% |

Stage 2 相对 Stage 4 的发行人先均值、再等权超额差为 `+2.31/+11.22/+6.10` 个百分点，说明结果不是只由历史最长发行人加权造成。但这仍是当前/历史热门股面板，不是无幸存者偏差的全市场组合。

### 时间分段

| 时段 | 21 日 Stage 2-4 平均超额 | 63 日 | 126 日 |
|---|---:|---:|---:|
| 2017-2022 | -0.01% | +5.32% | -2.79% |
| 2023-2026 | +2.35% | +9.30% | +19.02% |

正确动作是保留现有 Stage 风险约束，同时不增加 Stage 2 或高技术分奖励、不把 Stage 4 当机械做空信号、不根据 37 只热门股调参、不声称 entity matching 已被收益回测证明。它改善的是事件输入真实性。

## 最新热门股生产复验

Yahoo 当前榜单仍显示 ITRI/KNSA/LCID/IQV 等涨幅股，以及 INTC/NVDA/JBLU/SOFI/F/MARA/NU/MU/T 等高成交股。本轮新增一强一弱对照：

| 标的 | 真实动量背景 | depth | 技术 | 投资分 / 综合分 | 生产结论 |
|---|---|---|---|---:|---|
| LCID | 当日 +21.54%，1/3 月反弹；6/12 月 -23.7%/-39.1% | lite | Stage 4，技术维度 3，1 年最大回撤 -83.4% | 31.2 / 41.1 | 回避/谨慎，没有追逐单日上涨 |
| CLS | 当日 +10.04%，1/3 月 -5.72%/-24.63%，1 年 +83.56% | medium | Stage 2，技术维度 7，1 年最大回撤 -36.2% | 65.7 / 51.4 | 纯投资分到买入候选，但综合仍观望偏空 |

LCID 的 7 条新闻均以 Lucid/LCID 为主体；CLS 的 8 条新闻以 Celestica/CLS 财报为主。两份报告均 `critical=0`，唯一 warning 是 CLI 直跑允许缺失 `agent_analysis.json`。

与上一轮 KNSA `66.9`、OSCR `46.2`、ITRI `59.0`、MSTR `36.3` 相比，新结果继续说明单日热门与综合可买性不同。CLS 的 `65.7 buy_candidate` 只是冻结纯投资分档位，不等于生产综合结论。

报告：

- `skills/deep-analysis/scripts/reports/LCID_20260729/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/CLS_20260729/full-report-standalone.html`

## 冻结分支、事件护栏与性能

- baseline：`48e20fc4c9fe9823ab055155511be3bc503cb78b`
- candidate code：`91cb6eb22f8cac4970617c8036c5b3bc022426df`
- 文档起点：`a48f4b3b74f07a41ba1ef3b6b32b516602150a39`
- `86 raw + 7 synthetic = 93`
- 正向：`93 ok / 0 review / 0 possible_regression`，`7.915s -> 7.268s`
- 交换顺序：`93 ok / 0 review / 0 possible_regression`，`5.073s -> 6.682s`
- 两个顺序均 0 performance warning；只判无实质性能回退。
- 所有投资分、综合分、基本面分、panel consensus 与交易档位变化均为 0。
- active 官方 P0/P1 仍阻止不合理买入；伪造、resolved、过期、cross-issuer 事件仍不误伤。
- `113/113` direct tests、`py_compile`、`git diff --check` 通过。

SEC 因没有可确认的真实联系身份继续 fail-closed，本轮没有发 SEC 请求；CBOE 零请求。没有安装依赖、没有跑 deep、没有运行 update。

## 是否值得合回与停止线

建议吸收 entity matching 生产代码及真实数据/对抗门禁，也保留 walk-forward 工具、冻结价格和“不调动量分”的否证结论。本轮仍不自动合回正式分支，等待用户确认。

停止线：

1. 不为 1 条泛 Big Tech 标题放宽 issuer 主语要求。
2. 不把 founder/CEO、普通词、合作伙伴、供应商或交易对手当 alias。
3. 不把当前热门股面板当无偏全市场 alpha 回测。
4. 完整技术分数没有单调收益证据，不继续调权重。
5. Stage 的早期分段不稳定，不升级为单因子交易策略。
6. 没有点时财务/事件档案前，不回测“完整 UZI 综合分”。

## 下一步模型

- 默认：`GPT-5.6 Terra` + `中推理`，做正式分支 fast-forward 前的文件重叠/提交审计。
- 只有真实代码或事件消费冲突，或研究无幸存者偏差全市场历史宇宙时：`GPT-5.6 Sol` + `高推理`。
