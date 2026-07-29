# US entity 正式吸收与真实动量压力验证（2026-07-29）

## 结论

本轮值得把 `codex/scoring-validation-us-entity-recall-shadow` 以 fast-forward 吸收到正式开发分支 `codex/scoring-validation-guardrails`。收益来自发行人实体匹配的精度与召回改进，不来自评分调参。新增 AAL 真实生产审计进一步暴露并修复了法人名拆词中的行业通用词污染；冻结评分、交易档位和性能均无回退。

动量方向继续停止调参。37 股主回测只支持把 Stage 当作风险护栏；新增 8 股热门样本虽表现较强，但存在当前热门股选择与幸存者偏差，只能作为压力验证，不能升级为收益承诺或新买入规则。

## 分支与边界

- 正式基线：`48e20fc4c9fe9823ab055155511be3bc503cb78b`
- 候选代码提交：`3b8840b`
- 正式分支与隔离分支为纯 fast-forward 关系，没有代码冲突。
- `upstream/main=fce996c33e70eddce8e375f53cd252b549eb3d7c`；upstream push 保持 `DISABLED`。
- `main`、`codex/windows-local-stable` 未修改。
- 没有安装依赖，没有跑 deep，没有运行 update。
- 当前无可用于 SEC 请求的真实联系身份，因此未请求 SEC 并记录 access gap；CBOE 未联网。

## 真实样本与选择理由

实体 shadow 的三批冻结 Yahoo 新闻共 349 行，覆盖：

- 短 ticker：`MU/AI/C/F/NU/T`；
- 品牌与法人差异：`GOOGL/Alphabet`、`META`、`HOOD/Robinhood`、`XYZ/Block/Cash App`、`GEN/Norton/MoneyLion`；
- 常见词或歧义 ticker：`ON/IT/CAT/GEN`；
- 更名或多品牌：`MSTR/MicroStrategy/Strategy`、`XYZ/Block`、`GEN/Gen Digital`；
- 反向污染控制：BigBear.ai、Nu Skin、T. Rowe Price、供应商/合作方/前高管和交易对手方新闻。

本轮额外选择 Yahoo 当日活跃或涨幅榜中的 `AAL/PLUG/INCY/PLTR`：

| 股票 | 选择理由 | 深度 | 综合分 | 投资分 | Stage | 结论 |
|---|---|---:|---:|---:|---:|---|
| AAL | 高成交量、周期反弹、法人名含通用航空词 | lite | 43.7 | 46.8 | 2 | 回避 |
| PLUG | 高成交量、投机性强、弱基本面控制组 | lite | 39.5 | 34.2 | 1 | 回避 |
| INCY | 盈利质量与财报驱动上涨的对照组 | medium | 54.2 | 75.2 | 2 | 关注；综合仍观望偏空 |
| PLTR | 热门动量股但当日急跌，检验趋势护栏 | medium | 49.3 | 56.0 | 4 | 谨慎观察 |

与上一轮真实生产结果相比，`LCID=41.1/31.2/Stage 4/回避`，`CLS=51.4/65.7/Stage 2/综合观望偏空`。新旧样本都说明：单日上涨、热门度或高投资子分不会自动把综合结论升级为买入。

## alias 来源与身份绑定规则

1. ticker 来自当前证券标识；常见词 ticker 必须出现在明确证券语境中，不能做裸 substring。
2. 法人名来自 Yahoo quote 元数据；只移除公司后缀，保留至少两个词的完整法人基础短语。
3. 品牌、旧名和子品牌只能进入发行人 registry，且必须有发行人官网、IR 或可审计公司关系来源。
4. 不自动加入创始人、CEO、普通产品类别或名称相似实体。
5. partner、supplier、customer、former executive、deal counterparty 等关系只证明关联，不证明目标发行人是新闻主体。
6. `MU` 继续不得命中 `Musk`；`AI/C/F/IT/ON/CAT/NU/T` 等不得用无边界 substring。

本轮最小修复把 `airline/airlines/american` 视为不能单独拥有新闻的通用词，并把 `group/holding/holdings` 从法人基础名中移除；完整短语 `American Airlines` 仍保留，所以没有用牺牲真实召回来换精度。

## precision / recall / 污染 / 重复 / 新鲜度 / 延迟

三批冻结集在本轮代码下保持：

| 数据集 | 行数 | precision | recall | 跨发行人污染 | 重复率 | 中位新鲜度 | P95 新鲜度 | 中位采集延迟 | P95 延迟 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 命名难度主集 | 119 | 100% | 98.28% | 0 | 0 | 0.46 天 | 19.09 天 | 0.178s | 0.959s |
| 热门股独立集 | 80 | 100% | 100% | 0 | 0 | 0.37 天 | 4.74 天 | 0.263s | 0.941s |
| 短 ticker 第三集 | 150 | 100% | 100% | 0 | 0 | 0.61 天 | 22.57 天 | 0.228s | 0.879s |

合计 `TP=166/FP=0/FN=1`，precision `100%`、recall `99.40%`、跨发行人污染率 `0`。唯一 FN 是没有 META、Meta、Facebook 或 ticker 证据的泛 Big Tech 日程标题；继续 fail-closed 比扩大模糊匹配更安全。

AAL 生产事件的窄样本人工复核中，修复前接纳 9 条，修复后为 6 条；移除的 3 条分别以 United/Delta 合并传闻或泛航空股为主体。按这 9 条标题级审计，观察 precision 从 `6/9=66.7%` 提高到 `6/6=100%`，已知相关标题 recall 保持 `6/6=100%`。这是生产链窄审计，不与 349 行冻结集混算，也不外推为全行业总体精度。

## false positive / false negative 摘要

新增修复移除的 false positive：

- `United Approached Delta Last Year About Merging Airlines`
- `Forget United and Delta Talks, Airline Stocks Are Rising for a Different Reason`
- `United reportedly sought merger with Delta before approaching American`

保留的 true positive 包括明确出现 `American Airlines` 或 `AAL Stock` 的财报、收入、指引和成本标题。349 行冻结集中没有新增 false positive；唯一 false negative 仍是缺乏发行人实体证据的泛 Big Tech 标题，未修。

## 分支评分、档位与对抗性验证

- 正式 `48e20fc` 对候选 `3b8840b`：`92 raw + 7 synthetic = 99`，`99 ok / 0 review / 0 possible_regression`。
- 评分、投资分、综合分、决策档位全部零变化。
- active P0/P1 仍阻止不合理买入；伪造、已解决、过期和 cross-issuer 事件均不误伤。
- `MU` 不匹配 Musk；常见词 ticker 不产生 substring 污染。
- direct runner `128/128`；相关模块 `py_compile` 与 `git diff --check` 通过。

性能正向顺序为 `3.529s -> 3.948s`，交换顺序为 `4.572s -> 3.352s`；两次均无 performance warning。顺序噪声大，只能判定无性能回退，不能宣称提速。

## 真实历史 walk-forward

主验证使用 37 只美股加 SPY、10 年 Yahoo 复权日线、4518 个不重叠信号、下一收盘入场、21/63/126 日窗口和 20bp 摩擦：

| 指标 | 21 日 | 63 日 | 126 日 |
|---|---:|---:|---:|
| 技术分数对 SPY 超额 Spearman | 0.025 | 0.042 | 0.058 |
| 高分减低分平均超额 | +0.77 | +2.52 | -5.08 |
| Stage 2 减 Stage 4 平均超额 | +1.19 | +7.00 | +7.01 |

新增 `AAL/PLUG/INCY/PLTR/AMC/PATH/GLW/SNAP` 压力样本共 1103 个信号，技术分数超额 Spearman 为 `0.084/0.166/0.147`，高低分超额为 `+4.90/+12.15/+6.26`，Stage 2 减 Stage 4 为 `+3.43/+12.96/+36.89`。这组是按当前活跃度选出的事后小样本，126 日结果容易被少数强趋势股票放大；它只能说明代码在另一组真实价格上可运行且没有明显方向反转，不能取代更宽的主样本。

## 公允决策与停止线

值得吸收：

- 官方来源绑定的 alias registry；
- 带证券语境的短 ticker；
- 关系反向污染过滤；
- 本轮法人名完整短语保留与通用航空词拆分修复；
- 可复现 shadow、冻结 branch harness 和只读 walk-forward 工具。

继续停止或放弃：

- 不放宽 substring，不加入人物名或凭常识生成 alias；
- 不为剩余泛 Big Tech FN 增加弱实体匹配；
- 不根据 8 股热门样本调评分权重、动量参数、Stage 阈值或交易档位；
- 不把 Stage 2 当独立买入策略，不把历史相关性描述成真实收益保证；
- 没有无幸存者偏差的时点成分股宇宙前，不继续追逐更高回测收益；
- 没有真实 SEC 联系身份不请求 SEC；没有许可不访问 CBOE。

下一步若继续研究，使用 `GPT-5.6 Sol + 高推理`，目标应是构建按历史时点冻结、包含退市股和当期成分股的无幸存者偏差 US 宇宙；在该数据条件不满足时停止动量优化，转为监控实体匹配的新真实误报/漏报。
