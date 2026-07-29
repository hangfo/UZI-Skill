# 美股实体召回独立复采与热门动量验证

日期：2026-07-29

隔离分支：`codex/scoring-validation-us-entity-recall-shadow`

正式基线：`codex/scoring-validation-guardrails@48e20fc4c9fe9823ab055155511be3bc503cb78b`
候选代码检查点：`1a3b60b`

## 公允结论

本轮发现两个可重复、方向相反但可由同一精度优先原则解决的真实缺口：

1. `MSTR` 的明确前法人名 `MicroStrategy` 被漏召回；发行人官网明确说明 2025 年由 MicroStrategy 更名为 Strategy。
2. `Nvidia Partner SK Hynix...` 及“SK hynix 是 Nvidia 供应商”的摘要把另一发行人的财报误归给 NVIDIA。

最小候选仅加入有官方身份绑定的 MSTR 更名关系，把普通词 `Strategy` 限定为发行人事件句式，并排除 partner/supplier/customer 关系中的另一发行人事件。没有放宽 substring，没有把 Michael Saylor 等创始人姓名注册为 alias，也没有修改评分、动量、P0/P1 阈值或估值。

独立 80 条 Yahoo 真实新闻从 `TP=43/FP=1/FN=1/TN=20/ambiguous=15` 改为 `TP=44/FP=0/FN=0/TN=21/ambiguous=15`：precision `97.73%→100%`、recall `97.73%→100%`、跨发行人污染率 `2.27%→0`。上一轮 119 条集合仍为候选 `TP=57/FP=0/FN=1`，precision `100%`、recall `98.28%`、污染率 `0`，没有为了唯一泛 Meta 标题牺牲精度。

结论是：本轮最小修改值得吸收到正式评分分支，但仍遵守“不自动合回正式分支”；先推送隔离分支并交给独立复核。

## 真实样本与选择理由

### 实体盲审样本

独立复采 80 条，覆盖：

- 更名与普通词法人名：`MSTR/Strategy/MicroStrategy`。
- 当日涨幅榜且中长期动量强：`KNSA/OSCR/IQV`。
- 财报驱动的当日大涨：`ITRI`。
- 短期反弹但 6/12 月仍负：`LCID`，防止把单日涨幅误称长期动量。
- 跨发行人关系污染密集：`NVDA`。
- 长周期强但短周期回撤、短 ticker 回归控制：`MU`。

80 条均逐条标为 relevant、irrelevant 或 ambiguous；`relatedTickers` 只作审阅线索，不能让无实体泛标题自动变 relevant。冻结文件：

- `local-ops/state/us-entity-recall-shadow/20260729-hot-us-independent-before.json`
- `local-ops/state/us-entity-recall-shadow/20260729-hot-us-independent-labels.json`
- `local-ops/state/us-entity-recall-shadow/20260729-hot-us-independent-before-metrics.json`
- `local-ops/state/us-entity-recall-shadow/20260729-hot-us-independent-after-metrics.json`

重复率 `0`；Yahoo 请求延迟中位 `0.263s`、P95 `0.941s`。新闻年龄中位 `0.368 天`、P95 `4.741 天`，`98.75%` 在 7 天内、`100%` 在 30/90 天内。

### 热门动量样本

实时 Yahoo day_gainers/most_actives 与 chart v8 的 2026-07-28 收盘快照见：

`local-ops/state/us-entity-recall-shadow/20260729-hot-us-momentum-real.json`

关键观察：

- `KNSA`：1/3/6/12 月约 `+18.1%/+50.3%/+76.8%/+92.4%`，属于持续动量。
- `OSCR`：3/6/12 月约 `+43.4%/+161.0%/+113.5%`，但当前盈利质量仍弱。
- `ITRI`：当日 `+26.23%`，1/3 月约 `+26.7%`，由真实财报和指引触发。
- `LCID`：当日 `+21.54%`、1 月 `+31.8%`，但 6/12 月仍 `-23.7%/-39.1%`，只能称反弹。
- `MU`：6/12 月约 `+107.5%/+259.1%`，但 1/3 月 `-12.6%/-8.4%`，说明长周期强势已进入回撤。
- `IOND` 虽当日 `+25.8%`，但只有 1 个日线观察，明确从动量结论中剔除。

## alias 来源与身份绑定

- `MicroStrategy`：`https://www.strategy.com/company`，发行人官网明确说明 2025 年 2 月由 MicroStrategy rebrand 为 Strategy；作为 former legal name 接受完整 token。
- `Strategy`：`https://www.strategy.com/investor-relations`，官方 IR 把 `Strategy` 与 `Nasdaq: MSTR` 绑定；由于是普通词，只接受 `Strategy Announces/Reports/Completes/...` 或 `Strategy (MSTR)` 等发行人事件模板。
- 不加入 `Michael Saylor`：人物观点、个人社交内容和公司法定事件不是同一概念；只有摘要本身出现 `(Nasdaq: MSTR)`、Strategy 官方实体或 MicroStrategy 时才可入流。
- NVIDIA 关系句：`Nvidia Partner SK Hynix...` 及“supplier ... to Nvidia”归属 SK Hynix，不把目标公司作为 partner/supplier/customer 限定语就等同于目标公司事件。
- 所有已有 alias 继续要求 `kind/source_url/binding`；名称相似、常识关联、搜索结果位置和 Yahoo `relatedTickers` 均不构成新增 alias 的充分证据。

## false positive / false negative 摘要

修改前唯一 FP：

- `NVDA`：`Nvidia Partner SK Hynix Misses Q2 Sales Target But Profit Surprises`。事件主体是 SK Hynix，NVIDIA 只是关系限定语。实时 yfinance 的另一条摘要“SK hynix ... supplier ... to ... Nvidia”也被同一窄规则排除。

修改前唯一 FN：

- `MSTR`：`Michael Saylor Says Bitcoin Has Won, So Why Did MicroStrategy Stop Buying BTC?`。标题明确出现官方可验证的前法人名 MicroStrategy，候选恢复召回。

仍 fail closed：

- 两条只写 Michael Saylor 的 Bitcoin 观点标为 ambiguous；不把创始人姓名变成公司 alias。
- 上一轮 `Markets brace for Fed decision and Big Tech earnings` 仍为 FN；冻结元数据无 Meta、ticker 或品牌证据，不用查询位置猜测发行人。

## 真实生产评分与过程评估

使用项目 venv、默认 production pipeline、`--no-resume`，未跑 deep：

| 标的 | 深度 | 真实得分 | 档位 | 关键判断 |
|---|---|---:|---|---|
| KNSA | medium | 66.9 | 观察 | 增长 100、质量 80，但 PE 约 70、估值轴 28；高动量不等于无条件买入 |
| OSCR | lite | 46.2 | 回避 | 6 月动量很强，但 ROE/净利率为负、最大回撤约 -51.7%，质量轴仅 26 |
| ITRI | lite | 59.0 | 谨慎观察 | PE/PB 与质量较好，但 Stage 3、下跌趋势 cap 生效，财报跳涨不消除趋势风险 |
| MSTR | medium | 36.3 | 回避 | Stage 4、YTD 约 -37.2%、最大回撤约 -79.7%、增长和质量弱；旧名召回没有抬升买入结论 |

四份报告均生成且 `critical=0`：

- `skills/deep-analysis/scripts/reports/KNSA_20260729/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/OSCR_20260729/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/ITRI_20260729/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/MSTR_20260729/full-report-standalone.html`

与上一轮对比：

- 上轮真实生产 AAPL/AMD/MU 为 `50.2/48.0/52.6`，重点证明宏观缺失、路由和 MU/Musk 精度修复。
- 本轮换成强动量、反弹、更名和供应链污染混合篮子。KNSA 得分最高但仅“观察”；OSCR 即使 6 月涨幅约 161% 仍“回避”；说明模型没有因热门或当日涨幅机械追高。
- MSTR 上一冻结缓存 medium 为 `35.5`，本次最新真实生产为 `36.3`；`+0.8` 来自真实输入刷新。相同冻结输入的正式/候选分支仍是 `36.3→36.3`，不能把数据漂移归因于代码。

## branch-vs-branch、风险护栏与性能

正式 `48e20fc` 对候选 `1a3b60b`，加入 KNSA/OSCR/ITRI 最新缓存：

- `70 raw + 7 synthetic = 77`
- `77 ok / 0 review / 0 possible_regression`
- 所有投资评分、事件维度、交易档位变化均为 `0`
- MSTR lite/medium `35.1/36.3`、KNSA `65.7/66.9`、OSCR `46.2/46.2`、ITRI `59.0/59.0`，两分支完全一致
- active P0/P1 仍能阻止不合理买入；伪造、resolved、过期和 cross-issuer overlay 均未误伤
- direct runner `110/110`，覆盖 MU/Musk、common-word ticker、MSTR rebrand、NVIDIA partner/supplier、P0/P1 生命周期和 branch harness
- `py_compile` 与 `git diff --check` 通过

正序总进程 `5.725s→5.364s`，交换顺序为候选 `5.172s`、正式 `3.655s`；两轮 performance warning 均为 0。70 项纯评分中位在正序为 `0.006s→0.007s`，交换顺序为候选 `0.008s`、正式 `0.005s`。代码没有进入纯评分调用栈，绝对差只有毫秒级且受 worktree/缓存/负载影响；公允结论是“没有可识别的实质性能回退”，不宣称提速。

## SEC / CBOE 与数据边界

环境仍没有用户提供、可核验的 SEC 真实联系人身份，因此没有构造 User-Agent、没有请求 SEC，继续记录 access gap。MSTR 身份关系改由发行人官方官网和 IR 证明。

CBOE 未获许可，本轮完全未联网。Yahoo 数据仅用于本地研究验证，不对外再分发原始数据。

## 是否值得合回与停止线

建议：值得吸收，但本轮不自动合回正式分支。收益同时表现为独立真实集的 FN 和 FP 各减少 1，且旧 119 条集、评分、档位、P0/P1 边界和性能均无回退。

停止线：

- 不把 Saylor、Jensen Huang 等人物姓名自动注册为发行人 alias。
- 不把 `Strategy`、`AI`、`ON`、`IT` 等普通词恢复为裸 token 匹配。
- 不因 Yahoo `relatedTickers`、查询排名或摘要提及就认定发行人事件。
- partner/supplier/customer 排除只用于明确“另一发行人是事件主体”的关系句；若真实目标公司合资/合同事件出现漏召回，先 shadow，不扩大通用否定窗口。
- 不为热门股表现调评分权重、动量参数、P0/P1 阈值或估值参数。
- 未来独立集合出现任一跨发行人 FP 时，新 alias 继续留在 shadow。

下一步建议模型：`GPT-5.6 Terra + 中推理`，只做独立标签复核与合回前审计；若正式分支出现代码冲突，再升级为 `GPT-5.6 Sol + 高推理`。
