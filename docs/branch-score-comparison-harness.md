# 分支评分对照 Harness

日期：2026-07-08

## 目标

这个 harness 用同一批缓存输入，对比两个 git ref 的评分输出。它必须在任何评分公式改动被接受之前运行。

它的定位是中立裁判：

- 不重新抓行情数据。
- 不跑 deep。
- 不调权重。
- 不改评分公式。
- 只比较同一批 `raw_data.json` 在两个分支上的买卖决策是否发生回退。

核心问题是：

> 候选分支是否把某个样本的买卖决策改到了违反边界的位置？

## 当前基线

- 基线分支：`codex/windows-local-stable`
- 候选分支：`codex/scoring-validation-guardrails`
- 默认命令：

```powershell
D:\UZI-Skill\.venv\Scripts\python.exe tools\branch_score_compare.py `
  --baseline codex/windows-local-stable `
  --candidate codex/scoring-validation-guardrails `
  --mode both `
  --include-holdout `
  --label 20260708-core-holdout-both `
  --runner-timeout 600
```

输出是本地验证产物，位于：

```text
local-ops/state/branch-score-compare/
```

`local-ops/` 在这台 Windows 机器上按本地操作目录处理。可复用工具和测试放在仓库跟踪路径：

- `tools/branch_score_compare.py`
- `skills/deep-analysis/scripts/tests/test_branch_score_compare.py`

## 边界

- 不重新安装依赖。
- 不运行 update 脚本。
- 不运行 `--depth deep`。
- 本对照不重新抓市场数据。
- 优先使用缓存 `raw_data.json` 和纯评分函数。
- 不推送到上游 `wbh604/UZI-Skill`；只推送到个人 fork `hangfo/UZI-Skill`。
- 除非这个 harness 或同等中立测试证明存在交易决策质量问题，否则不要调评分公式。

## 样本分层

### 缓存 Raw Data

缓存篮子使用本机真实 `.cache/<ticker>/raw_data.json` 快照。

核心样本：

- `600519.SH`：A 股质量/价值控制样本。
- `00700.HK`：港股平台型质量控制样本。
- `AAPL`：美股盈利巨头，带估值约束。
- `MSTR`：加密资产财务杠杆/高波动风控样本。
- `AXTI`：投机小盘股对抗样本。

Holdout 样本：

- `CRCL`：稳定币、IPO 波动、监管催化样本。
- `SIVE.ST`：瑞典市场兼容性、亏损/高估值样本。
- `688017.SH`：机器人减速器成长股，高估值压力样本。

### Synthetic Feature 样本

这些样本直接调用 `compute_investment_score()`，用于在不依赖网络数据的情况下压测决策边界。

- `theme_only_microcap`：题材很热，但质量弱、风险极高。
- `quality_compounder_no_momentum`：质量耐久，但趋势和增长偏弱。
- `expensive_profitable_platform`：高质量平台，但估值压力大。
- `high_quality_stage3_confirmed_downtrend`：高质量公司，但处于确认下跌的 Stage 3 出货/分配阶段。
- `stage4_missing_price_high_quality`：高质量公司，但 Stage 4 且缺少价格确认数据。
- `a_share_youzi_heat_institutional_selling`：A 股游资热度高，但基本面弱。
- `missing_financials_theme_heat`：财务数据缺失，但题材热度和分析师乐观度高。

### Synthetic Raw Data 样本

这些样本走和缓存 raw data 相同的链路：

```text
score_dimensions -> generate_panel -> generate_synthesis
```

它们覆盖 feature-only 测试看不到的字段契约和数据质量边界：

- `__synthetic_empty_recent_news_stale_legacy`：`recent_news` 存在但为空时，不能回退到旧字段 `news` 的过期内容。
- `__synthetic_single_strong_negative_event`：单条严重负面事件也必须影响 `15_events`，不能要求重复出现很多次才扣分。
- `__synthetic_negated_negative_event`：`无违规`、`未发现欺诈`、`settled lawsuit` 这类否定语境不能被误罚。
- `__synthetic_missing_financials_raw`：财务数据缺失时不能崩溃，也不能被题材热度推成高置信买入。

## 判定

- `ok`：没有违反决策边界。
- `review`：分数漂移或档位变化值得人工查看，但不自动判定为回退。
- `possible_regression`：候选分支违反了样本的特定边界，例如风险样本被升级，或事件字段契约失败。

决策档位：

| 档位 | 分数区间 |
|---|---:|
| `avoid` | `< 40` |
| `cautious` | `40 <= score < 55` |
| `watch` | `55 <= score < 65` |
| `buy_candidate` | `65 <= score < 80` |
| `strong_buy` | `>= 80` |

## 回退标记

重要标记包括：

- `quality_control_downgrade`：质量控制样本被降档。
- `risk_control_upgrade`：风险控制样本被升档。
- `speculative_promoted_to_buy`：投机观察样本被推成买入或强买。
- `below_candidate_floor` / `above_candidate_ceiling`：候选分数越过样本边界。
- `15_events_below_floor` / `15_events_above_ceiling`：事件维度违反 synthetic raw-data 字段契约。
- `large_score_drift`：绝对分数漂移达到 8 分或以上。
- `decision_tier_changed`：买卖档位发生变化。

只有边界违反类标记会被判为 `possible_regression`。单纯大幅漂移但未违反边界时，只判为 `review`。

## 归因与置信度

Harness 现在会为每一行输出稳定的解释层：

- `explanation.category`：机器可比较的归因枚举。
- `explanation.label`：中文归因标签。
- `explanation.rationale`：面向人工复核的一句话解释。
- `explanation.metrics`：定量证据，包括分数漂移、档位漂移、边界余量和主要轴向变化。
- `explanation.confidence`：本次判定的证据完整度，不是收益预测胜率。
- `explanation.support`：同类归因的交叉支持强度，用于识别过拟合风险。
- `explanation.reliability`：综合置信度、交叉支持和阈值敏感性的整体可靠性。

### 归因类别

| 类别 | 含义 | 典型处理 |
|---|---|---|
| `execution_failure` | 某个分支执行失败或输出缺失。 | 先修 harness/环境，不解读分数。 |
| `field_contract_violation` | synthetic raw-data 字段契约失败，例如 `15_events` 越界。 | 优先检查字段读取、fallback 和语义解析。 |
| `quality_control_possible_downgrade` | 质量控制样本被降档或跌破下限。 | 检查是否误伤高质量公司。 |
| `risk_control_suspicious_upgrade` | 风险样本被升档或越过上限。 | 检查是否放松风控或题材加分过强。 |
| `speculative_promoted_to_buy` | 投机观察样本进入买入档。 | 检查是否把题材热度当成买点。 |
| `risk_control_reasonable_tightening` | 风险样本分数/档位下调。 | 通常是合理变化，但仍看漂移幅度。 |
| `trend_guardrail_tightening` | Stage 3/4 或下跌趋势样本被降档。 | 通常是趋势护栏生效。 |
| `data_quality_uncertain` | 样本主要检验数据缺口或事件语义。 | 不直接调公式，先检查输入质量。 |
| `material_score_drift` | 大幅分数漂移但未违反硬边界。 | 人工复核轴向变化是否合理。 |
| `decision_tier_shift` | 买卖档位变化但未违反样本边界。 | 结合边界余量判断是否贴边。 |
| `stable_no_material_change` | 分数和档位基本稳定。 | 可视为通过。 |
| `neutral_or_small_change` | 小幅变化或无明确方向性边界。 | 低优先级复核。 |

### 定量判定方式

每行会给出以下指标：

- `abs_score_delta`：候选分支相对基线的绝对分数漂移。
- `tier_delta`：买卖档位变化，正数代表升档，负数代表降档。
- `boundary_checks`：每个样本边界的值、阈值和余量。
- `boundary_violations`：余量为负的边界，直接支持 `possible_regression`。
- `nearest_boundary_distance`：候选结果距离最近边界的分数；越接近 0，越需要人工复核。
- `threshold_sensitivity`：只做报告层敏感性，不改阈值；显示结论是否容易被 1/3/5 分边界扰动影响。
- `top_axis_deltas`：质量、增长、催化、估值、风控等轴向的最大变化。

边界余量规则：

- 对 `min_candidate_score`：余量 = 候选分数 - 下限。
- 对 `max_candidate_score`：余量 = 上限 - 候选分数。
- 对维度上下限同理。
- 负数表示越界；`0~1` 分表示贴边，置信度会下调。

### 置信度

`confidence.score` 从证据完整度角度给出 0-100 分：

- `high`：`>= 75`，证据完整、离边界较远或边界违反明确。
- `medium`：`50-74`，证据可用但存在贴边、弱预期或仅 review。
- `low`：`< 50`，存在执行失败、分数缺失或严重数据不足。

会降低置信度的因素：

- 分支执行失败或缺少输出。
- 缺少 `investment_score`。
- 候选结果距离边界 `<= 1` 分或 `<= 3` 分。
- 样本没有强预期方向，例如 `neutral`。
- 样本本身是数据缺口边界，例如 `data_gap`。
- 只触发 `review`，没有违反硬边界。

因此，“不可靠”不是主观判断，而是以下情况之一：

- `confidence.level == low`。
- 存在 `execution_failure`。
- `nearest_boundary_distance <= 1` 且只靠单个样本支持结论。
- 样本属于 `data_quality_uncertain`，但缺少字段级证据。
- 同一原因只在 synthetic 样本出现，真实缓存 raw data 没有交叉支持。

### 交叉支持

交叉支持不改变 `ok/review/possible_regression`，只衡量某个归因是否可能过拟合当前样本。

| 支持等级 | 判定方式 | 含义 |
|---|---|---|
| `strong` | 同类归因至少 4 条，且同时覆盖真实缓存、synthetic 样本和 lite/medium 模式。 | 证据来源相对独立，过拟合风险较低。 |
| `moderate` | 同类归因至少 2 条，并覆盖多来源或真实缓存的 lite/medium。 | 有交叉证据，但覆盖还不完整。 |
| `limited` | 同类归因至少 2 条，但来源类型单一。 | 可作为提示，不能单独外推。 |
| `isolated` | 同类归因只有 1 条。 | 只说明这个样本，不说明普遍规律。 |

理论依据：

- **同输入对照**：两个分支只比较同一批冻结输入，减少数据刷新造成的混杂变量。
- **分层样本**：真实缓存 raw data、synthetic feature、synthetic raw-data 分别覆盖现实分布、极端边界和字段契约。
- **留出样本**：core basket 与 holdout 分开，避免只在已知样本上解释得漂亮。
- **硬边界优先**：只有越过预设边界才判 `possible_regression`，解释层不能单独制造回退结论。
- **交叉支持约束**：同类归因必须跨来源或跨模式重复出现，才提高解释可信度。

仍需防范的过拟合：

- Synthetic 样本是人为构造的，适合检查边界，不代表真实市场频率。
- 当前缓存 raw data 数量有限，不能证明公式“更好”，只能证明未触发已定义边界回退。
- 阈值如 55/65/8 分漂移是工程护栏，不是统计显著性结论。
- 如果未来新增样本后归因分布大幅改变，应优先扩样本和复核边界，而不是调公式迎合旧结果。

### 可靠性

`confidence` 只看单行证据完整度，`support` 只看同类归因的交叉来源，`reliability` 把两者和阈值敏感性合并。

这能避免一个常见误读：

> 单个 synthetic 样本可能 `confidence=high`，因为字段齐全、边界明确；但如果 `support=limited` 且贴近边界，`reliability` 会被降到 `medium/low`。

可靠性不改变回退判定，只决定结论能说多满：

- `high`：可以作为当前 harness 的稳定证据。
- `medium`：方向可信，但需要更多真实缓存样本或边界复核。
- `low`：只能作为提示，不应外推，也不应据此调公式。

## 最新已知结果

扩展版运行结果：

```text
label: 20260709-offline-reliability-core-holdout-both
result: 29 ok / 2 review / 0 possible_regression
```

输出文件：

```text
local-ops/state/branch-score-compare/20260709-offline-reliability-core-holdout-both.md
local-ops/state/branch-score-compare/20260709-offline-reliability-core-holdout-both.json
```

离线纯评分耗时：

- baseline: `3.1s`
- candidate: `2.6s`
- performance warnings: `0`

两个 `review` 都是预期内的风险收敛，不是公式回退：

- `high_quality_stage3_confirmed_downtrend`：`66.0 -> 59.0`，档位 `buy_candidate -> watch`，归因为 `trend_guardrail_tightening`，置信度 `high(82)`，交叉支持 `limited`。
- `stage4_missing_price_high_quality`：`66.0 -> 59.0`，档位 `buy_candidate -> watch`，归因为 `trend_guardrail_tightening`，置信度 `medium(64)`，交叉支持 `limited`，可靠性 `low(40)`；因为候选分数贴近上限边界，仍需人工复核但不判回退。

这两个变化说明候选分支阻止了 Stage 3/4 下的质量保底误触发买入信号；但由于目前主要由 synthetic 样本支持，结论应表述为“方向合理、需要真实缓存样本继续交叉验证”，不能过度外推。

归因汇总：

- `stable_no_material_change`: 14
- `risk_control_reasonable_tightening`: 11
- `data_quality_uncertain`: 4
- `trend_guardrail_tightening`: 2

置信度汇总：

- `high`: 24
- `medium`: 7
- `low`: 0

交叉支持汇总：

- `strong`: 25
- `limited`: 6

可靠性汇总：

- `high`: 21
- `medium`: 7
- `low`: 3

低可靠项集中在 synthetic-only 且贴边的边界样本：

- `__synthetic_single_strong_negative_event` 的 lite/medium 两行：数据质量归因，单条负面事件边界余量只有 `0.9`。
- `stage4_missing_price_high_quality`：趋势护栏归因，但交叉支持仍是 `limited`，且边界余量为 `0.0`。

这些低可靠项不推翻 `0 possible_regression`，但限制了结论外推范围：它们只能说明当前字段契约/边界行为符合预期，不能证明真实市场分布里已经充分覆盖。

`limited` 主要集中在数据质量 synthetic raw 样本和 Stage 3/4 趋势护栏 synthetic 样本。它们适合证明字段契约和边界行为，但还不能单独证明真实市场分布中的普遍性。

Synthetic raw-data 检查也显示字段契约符合预期：

- 空 `recent_news` + 旧 `news`：基线 `15_events=8`，候选分支 `15_events=5`。
- 单条强负面事件：基线 `15_events=5`，候选分支 `15_events=4`。
- 否定负面事件：基线 `15_events=5`，候选分支 `15_events=5`。
- 财务缺失 raw 样本：候选分支保持 `cautious`，没有变成买入。

以后如果出现非零 `possible_regression`，先检查具体样本证据，再决定是否修改评分公式。

## 后续非破坏性优化

在不调公式、不抓新数据的前提下，后续可继续增强以下验证层：

1. **真实缓存补盲**：优先寻找已有缓存中 Stage 3/4、财务缺失、单条负面事件等真实样本，把 currently `limited` 的归因提升到 `moderate/strong`。
2. **阈值敏感性检查**：不改阈值，只在报告里计算“如果边界上下浮动 1/3/5 分，判定是否改变”，用于发现贴边结论。
3. **模式一致性检查**：同一 ticker 的 lite/medium 如果归因相反，应降置信度或标记 review。
4. **轴向贡献一致性**：如果分数变化主要来自目标修复轴，例如 risk_control 或 events，解释更可信；如果来自无关轴，标记为复核。
5. **新增 holdout 批次**：只用已有缓存或人工构造 raw-data，不运行 update；新增后先看旧结论是否仍保持，而不是按新样本调公式。

## 真实缓存补盲与在线证据冻结

2026-07-09 增加了独立审计入口：

```powershell
D:\UZI-Skill\.venv\Scripts\python.exe tools\branch_score_compare.py `
  --audit-cache-blindspots `
  --label 20260709-real-cache-blindspot-plan
```

这个入口只做样本覆盖审计和补盲计划，不运行分支对照，也不改评分公式。最新审计结果：

| 盲点目标 | 状态 | 真实缓存覆盖 | 市场覆盖 | 结论 |
|---|---|---:|---:|---|
| `negative_event` | gap | 0/2 | 0/2 | 缺少真实缓存负面事件样本；不能用 synthetic 结果外推。 |
| `missing_financials` | gap | 0/2 | 0/2 | 缺少真实财务缺失样本；当前只能证明字段契约和风控边界。 |
| `stage3_4` | satisfied | 4/4 | 3/3 | Stage 3/4 趋势护栏已有真实缓存交叉支持。 |
| `lhb_activity` | satisfied | 2/1 | 1/1 | A 股龙虎榜/游资热度已有真实缓存覆盖。 |

审计工具的约束：

- 只把 `core`、`holdout`、`extra`、`discovered_cache` 计入真实缓存覆盖。
- `synthetic_feature` 和 `synthetic_raw` 只能证明边界与字段契约，不能冒充真实市场覆盖。
- 真实缓存缺口不会导致自动调公式；它只降低结论外推强度。

在线补证据的最佳方案不是在 branch comparison 运行时临时联网，而是分两步：

1. **在线证据构建**：按官方来源优先、日期排序、固定 universe 的方式检索，写入冻结 overlay，例如 `local-ops/state/evidence-overlays/<ticker>.json`。每条证据必须包含 source、url、title、published_at/fetched_at、字段映射和失败原因；拿不到就记录缺口，不能补经验判断。
2. **离线分支对照**：只读取已经冻结的 raw data 或 overlay，用同一份输入分别跑 baseline/candidate。运行时继续设置 `UZI_SCORING_OFFLINE=1` 和 `UZI_QUANT_SIGNAL_OFFLINE=1`，避免性能和输入漂移。

按市场的来源优先级：

- A 股负面事件：巨潮公告、交易所纪律处分、证监会处罚、公司公告。
- A 股财务缺失：巨潮年报/中报、交易所披露、东财财务表；字段级补齐，不整体替换原源。
- 港股负面事件：HKEXnews、SFC enforcement、公司公告。
- 港股财务缺失：HKEXnews 年报/中报、公司 IR。
- 美股负面事件：SEC EDGAR 8-K/10-K 风险事件、SEC litigation releases、公司 IR。
- 美股财务缺失：SEC EDGAR 10-K/10-Q/XBRL、公司 IR。

防过拟合原则：

- 先冻结候选 universe，再看分支分数变化。
- 按盲点缺口选样，不按“能证明候选分支更好”的方向选样。
- 优先从官方列表按日期取前 N 个可映射 ticker；检索失败也进入审计记录。
- 新在线样本先作为冻结证据进入 holdout，不直接推动公式调整。
- 如果某结论只来自 synthetic，即使单行 confidence 高，也只能给 limited support。

### Evidence Overlay 构建器

2026-07-09 新增最小闭环工具：

```powershell
D:\UZI-Skill\.venv\Scripts\python.exe tools\evidence_overlay_builder.py `
  --ticker AAPL `
  --target missing_financials `
  --max-items 2
```

输出默认写入：

```text
local-ops/state/evidence-overlays/<ticker>-<target>.json
```

当前支持：

- `missing_financials`：美股走 SEC `company_tickers.json` + `companyfacts`，只做字段映射，不生成投资分数。
- `negative_event / US`：SEC `submissions` 的 8-K item code、SEC litigation releases、SEC trading suspensions。
- `negative_event / A`：证监会行政处罚决定、巨潮动态 `orgId` 映射后的公司公告；`.SH` 直连上交所监管措施；`.SZ` 直连深交所监管措施与纪律处分。
- `negative_event / HK`：HKEX issuer critical filings、HKEX disciplinary overview 的精确 `Stock Code`；SFC enforcement 列表与正文中的精确 `stock code`。
- 缓存新闻只有在 URL 属于已知官方域名、ticker 归属可精确确认、标题命中明确 taxonomy 时才可成为正式证据；不靠泛新闻情绪或常识推断。
- `--no-network`：只读本地缓存，用于测试和离线复跑。
- `--no-write`：只打印状态，不落地 overlay。
- `--as-of YYYY-MM-DD`：冻结时效判断基准，确保跨分支、跨机器复跑一致。
- `--lookback-days`：统一时效窗口，默认 730 天，边界日计入，未来日期和无日期记录剔除。
- `--source-record-limit`：限制 SFC 等列表正文扫描数量，默认 60；它是性能边界，不代表历史全集。

负面事件优先级：

| 级别 | 定义 | 当前 SEC 8-K 映射 | 用途 |
|---|---|---|---|
| `P0` | 财报可信度或持续经营硬风险 | `1.03` 破产/接管、`4.02` 财报不可依赖 | 必须触发最高优先级复核，通常应限制买入信号。 |
| `P1` | 重大风险升级 | `1.05` 重大网络安全、`2.04` 债务触发、`2.05` 退出/处置成本、`2.06` 重大减值、`3.01` 退市通知、`4.01` 审计师变更 | 阻止高置信买入，进入风险复核。 |
| `P2` | 需要上下文的经营/法律风险 | 目前不从 SEC item 自动判定；只接受明确可追溯标题/来源 | 只作为 review 证据，不单独硬降级。 |

扩展原则：

- 先接“一个 adapter 覆盖一类市场”的官方结构化源，例如 SEC submissions，而不是按个股或新闻站点逐个接。
- 每个 adapter 必须输出同一 overlay schema：`source/url/title/published_at/fields/severity/event_type`。
- 新 adapter 先只进入 overlay，不直接进入评分公式；接入 branch harness 后仍然复用同一份冻结输入。
- 没有明确官方字段或可追溯标题时，状态保持 `gap/partial`，不能为了覆盖率提高而扩大关键词。
- 实体归属优先使用官方证券代码；`700` 不得匹配 `1700`，名称只能作为辅助，不允许模糊子串直接进入评分输入。
- 公司/发行人直接受罚可进入 `P0/P1`；仅前董事、前主席或其他关联人受罚降为 `P2`，不能单独生成 `ready`。
- 问询函、关注函及其回复不是处罚证据；监管工作函也不自动升级为负面事件。
- 同一交易所决定若同时出现在交易所原文和巨潮公司公告，优先保留交易所原文，并把巨潮 URL 记录为 corroborating provenance，避免重复加权。
- `status=ready` 仍需官方域名、精确实体匹配、有效日期和至少一条 `P0/P1`；手工把 `P2` 标成 ready 也会被 harness 拒绝。

实际验证：

```text
AAPL missing_financials -> ready / high confidence / ~5.8s
AAPL negative_event -> gap / low confidence / ~2.3s
SMCI negative_event -> ready / high confidence / ~2.2s
```

`SMCI negative_event` 的真实命中来自 SEC submissions 中的 8-K Item `3.01`，即退市或持续上市规则不满足通知，属于 `P1`。这说明 adapter 能捕捉官方结构化负面事件；`AAPL negative_event` 保持 `gap` 则说明它不会在无 P0/P1 证据时为了覆盖率而误报。

解释边界：

- overlay 是“事实证据冻结层”，不是评分层。
- overlay 可以补足真实信息，但只有冻结后才能作为同一份输入喂给 baseline/candidate。
- 如果官方源不可达、字段缺失或证据语义不明确，状态必须是 `gap` 或 `partial`，不能用经验判断补齐。
- 性能上，在线构建是预处理步骤；branch-vs-branch harness 仍保持离线数秒级。

### Overlay-backed 分支对照

冻结 overlay 通过显式开关接入 branch harness：

```powershell
D:\UZI-Skill\.venv\Scripts\python.exe tools\branch_score_compare.py `
  --baseline codex/windows-local-stable `
  --candidate codex/scoring-validation-guardrails `
  --mode both `
  --include-holdout `
  --include-discovered-cache `
  --include-evidence-overlays `
  --label 20260709-overlay-backed-check
```

接入规则：

- 只读取 `status=ready` 的 `uzi.evidence_overlay.v1`。
- 当前只把 `negative_event` overlay 转为 raw-data 同链路样本。
- `gap`、`partial`、schema 不匹配或缺少 `title/url/severity` 的 overlay 不进入对照。
- overlay 样本的 evidence type 是 `frozen_overlay`，不冒充 `cached_raw` 或 synthetic。
- `P0` 要求事件维度低于中性并限制总分；`P1` 主要限制高置信买入，不强制事件维度低于中性；`P2` 只作为 review 证据。
- branch runner 仍然离线运行；overlay 是运行前冻结好的输入，不在对照过程中联网。

### 2026-07-13 三市场官方负面事件验证

冻结基准统一为 `as_of=2026-07-13`、`lookback_days=730`。在线构建只发生在对照前；branch runner 仍完全离线。

| 市场 | 样本 | 官方命中 | 冻结状态 | 用途 |
|---|---|---|---|---|
| US | `SMCI` | SEC 8-K `3.01`、`4.01` | `ready/P1` | issuer 级真实正例 |
| US | `HUBG` | SEC 8-K `4.02`、`3.01` | `ready/P0+P1` | 财报不可依赖与上市规则真实 P0/P1 |
| A / SZSE | `002038.SZ` | 巨潮公司公告、深交所纪律处分/监管函 | `ready/P1+P2` | 多源交叉正例与镜像去重 |
| A / SZSE | `000851.SZ` | 证监会处罚、巨潮重大违法退市风险、深交所处分 | `ready/P0+P1` | 监管/发行人/交易所三层真实正例 |
| A / SSE | `601872.SH` | 巨潮行政监管措施公告、上交所监管警示 | `ready/P1+P2` | 上交所直连正例 |
| A / SSE | `600519.SH` | 时效窗口内无 eligible P0/P1 | `gap` | 不从历史旧记录推断当前负面 |
| HK | `03616.HK` | HKEX issuer disciplinary action | `ready/P1` | issuer 级真实正例 |
| HK | `00841.HK` | HKEX issuer critical filing | `ready/P1` | 发行人关键公告真实正例 |
| HK | `00171.HK` | HKEX former director action | `partial/P2` | 关联人不冒充 issuer 处罚 |
| HK | `06161.HK` | SFC former chairman proceeding，正文精确代码 `6161` | `partial/P2` | SFC 实体匹配反例 |

SFC 在线构建单 ticker 扫描最近 40 条 enforcement 正文时约 13-20 秒；同时并行构建 3 个 HK ticker 会因官方端点竞争升到约 47-50 秒，因此应顺序冻结或复用已有 overlay，不要把多个 SFC 全文扫描并发运行。A 股官方 adapter 约 1-3 秒，美股 SEC 约 2-6 秒。该耗时只属于一次性证据冻结，不进入评分运行；本次 baseline/candidate 评分分别约 `2.7s/2.4s`。

为同时验证“输入接通”和“交易决策敏感性”，每个 `ready` overlay 生成两类样本：

- 最小 raw 同链路样本：证明 frozen overlay 确实被两分支消费。
- 市场匹配反事实样本：US 注入 AAPL 缓存、A 股注入 600519.SH、HK 注入 00700.HK；只替换/追加 `15_events.recent_news`，其余缓存原样保留。它明确标记为 counterfactual，不冒充事件属于基础股票。

#### 问题发现阶段（修复前）

修复前对照共 `47` 行：`37 ok / 2 review / 8 possible_regression`。8 行回退来自 4 个反事实样本在 lite/medium 的重复验证，不是 8 个独立事实：

| 反事实 | 基线 `15_events` | 候选 `15_events` | 候选总分/档位 | 结论 |
|---|---:|---:|---|---|
| `002038.SZ P1 -> 600519.SH` | 5 | 6 | 59 / watch | 负面事件反而提高事件维度，违反字段契约 |
| `601872.SH P1 -> 600519.SH` | 5 | 6 | 59 / watch | 同上 |
| `03616.HK P1 -> 00700.HK` | 5 | 7 | 59 / watch | HKEX disciplinary title 被当成普通正向新闻 |
| `SMCI P1 -> AAPL` | 5 | 5 | 68 / buy_candidate | `delisting` 未触发英文负面词表，未阻止买入候选 |

根因定位到 `score_fns.py` 的事件评分仍只解析标题关键词，不读取 overlay 已冻结的 `severity/entity_scope/official_source`：A/HK 官方标题中的“纪律处分/监管措施/Disciplinary Action”和英文 `delisting` 没有按结构化 P1 处理，部分记录还被计入 positive bonus。

本轮因此得出“存在明确交易决策问题”的结论。后续修改严格限于事件证据消费契约和买入护栏，没有调整权重或其他维度公式。

效果评分采用可复核的双评分，避免把“测试工具发现问题”和“现有评分已经解决问题”混为一谈：

- 修复前 adapter + harness 交付：`9.0/10`。它准确暴露了交易决策问题，但当时评分端尚未消费结构化风险。
- 修复前评分对结构化 P1 的处理：`4.0/10`。这是能力评估分，不是 `15_events` 风险维度分。

### 2026-07-13 结构化事件消费契约与最终复验

最小消费契约已经实现，未调整普通样本的权重：

- 只有官方域名、`official_source=true`、`entity_match=exact`、issuer 直接事件、有效 `age_days` 的 P0/P1 才能触发交易护栏。
- P0 将 `15_events` 上限设为 `2`、可买性分数上限设为 `59.9`；P1 分别为 `4` 和 `64.9`。
- P2、关联人事件、已解决/已整改事件只保留审计信息，不硬降当前交易档位。
- 非官方 URL、模糊实体、未来日期、超过 730 天、非数字日期、镜像重复记录都不能借结构化字段获得 P1 权限。
- 没有结构化字段的旧 raw data 继续走原标题 fallback；结构化负面行不再被普通 positive-news bonus 反向奖励。
- `overall_score/legacy_overall_score` 保持旧排序语义；护栏只作用于面向交易的 `investment_score`。

最终对照报告为 `local-ops/state/branch-score-compare/20260713-structured-event-contract-final.md`。输入包含 core、holdout、真实冻结 overlay、市场匹配反事实和合成对抗样本，共 `67` 项：

| 结果 | 数量 | 解释 |
|---|---:|---|
| `ok` | 61 | 满足样本边界，核心/holdout 未出现非预期退档。 |
| `review` | 6 | HUBG P0、SMCI P1 在 AAPL 反事实中按设计阻止买入候选，各由 lite/medium 复验；另 2 项是既有 Stage 3/4 护栏。 |
| `possible_regression` | 0 | 没有硬边界违规。 |

关键决策变化：

| 样本 | 修复前 | 修复后 | 解释 |
|---|---|---|---|
| `HUBG P0 -> AAPL` | `68 / buy_candidate`、事件维度 5 | `59.9 / watch`、事件维度 2 | 财报不可依赖等 P0 阻止买入。 |
| `SMCI P1 -> AAPL` | `68 / buy_candidate`、事件维度 5 | `64.9 / watch`、事件维度 4 | 退市/审计风险阻止高置信买入。 |
| 伪造非官方 P1 | 事件维度 5 | 事件维度 5 | 不信任自报 severity。 |
| 已解决 P1 | 事件维度 5 | 事件维度 5 | 历史可审计，不压当前决策。 |
| 超时效 P1 | 事件维度 5 | 事件维度 5 | 不用陈旧/未来证据制造风险。 |

本次客观效果评分：

- 结构化 P1 处理能力：`8.8/10`，由修复前 `4.0/10` 提升。消费正确性 `2/2`、交易边界 `2/2`、对抗防护 `2/2`、三市场真实证据 `1.8/2`、事件解决态自动追踪 `1.0/2`。最后一项未满分，因为当前只消费已冻结的 `resolution_status`，还没有自动关联后续解除/整改公告。
- adapter + harness：`9.3/10`。90 个直接测试、67 项分支比较、三市场官方正反例和 0 个硬回退；扣分来自 SFC/部分列表仍为有界扫描，以及 NYSE/Nasdaq 动态列表没有稳定 schema，未强行接入。
- 整体交付：`9.0/10`。已修复经过中立对照证明的交易问题，且没有通过扩大词表、挑样本或调高权重换取分数。

注意：这里的能力评分 `8.8/10` 与事件维度 `15_events=4/10` 含义不同。后者是 P1 风险存在时的风险分，不应为了能力评分好看而提高。

### 2026-07-13 官方解决态生命周期与真实数据复验

解决态不是事件行可以自行声明的布尔值。当前消费契约要求同时满足：

- 解决记录晚于原事件，且不晚于冻结样本的 `as_of`；
- 官方 URL、`entity_match=exact`、`entity_scope=issuer`；
- `linked_event_id` 精确指向当前 canonical event，source record 与 URL 均不能自引用；
- `lifecycle_topic` 完全相同；
- SEC archive 的原事件与解决记录必须解析到同一 EDGAR CIK。

builder 当前只自动识别 Nasdaq Rule `5250(c)(1)` 周期报告合规主题。理由是该主题存在可机械验证的官方终态组合：后续 8-K 同时声明公司已经合规且 matter closed。以下情况不得扩张为“已解决”：临时 exception、延期、提交整改计划、预计未来合规、泛化 remediation、处罚缴清、欺诈调查、财报不可依赖、审计师变更。

真实冻结输入来自 SEC 官方页面，不以 mock 或搜索摘要得出效果结论：

| 发行人 | 官方记录 | 生命周期结论 |
|---|---|---|
| SMCI | 2024-09-20、2024-11-20 Item 3.01 | 明确不符合 Rule 5250(c)(1)，active P1。 |
| SMCI | 2024-12-06 Item 3.01 | Nasdaq 给出临时 exception，仍 active。 |
| SMCI | 2025-02-26 Item 3.01 | 明确 now complies 且 matter is now closed，精确关闭前述 3 条。 |
| SMCI | 2024-10-30、2024-11-18 Item 4.01 | 不属于同一窄主题，继续 active P1。 |
| HUBG | 最新窗口内官方 8-K | 有 P0/P1，但没有 Rule 5250(c)(1) 终态匹配，`no_match`。 |
| AAPL | 最新窗口内官方层 | 无 eligible P0/P1，保持 `gap`，不从缺失推断安全或解决。 |

混合 overlay 会生成四个 raw case：原样 active、市场匹配 active 反事实、拆出的 verified-resolution 影子、市场匹配 resolution 反事实。这样可以同时证明风险仍被消费，以及解决态没有对当前交易结论造成惩罚或奖励。

最终报告为 `local-ops/state/branch-score-compare/20260713-real-event-lifecycle-final.md`：`64 raw + 7 synthetic = 71` 项，lite/medium 全部运行，结果 `71 ok / 0 review / 0 possible_regression`。所有 score delta 与 tier delta 为 0。正式报告单次 baseline/candidate 为 `1.697s/1.807s`；同一正式 commit 三次中位数为 `1.697s/1.696s`，单次差异在 `-5.8%` 到 `+6.5%` 间反向波动，均无性能告警，因此只判定无回退。

关键真实反事实：

| 样本 | investment / tier | `15_events` | 解释 |
|---|---:|---:|---|
| SMCI active+resolved 原样 | `64.4 / watch` | 4 | 两个未解决 Item 4.01 仍保留 P1。 |
| SMCI active 事件注入 AAPL | `64.9 / watch` | 4 | 未解决 P1 仍阻止高置信买入。 |
| SMCI verified-resolution 影子 | `64.4 / watch` | 5 | 事件维度不再受历史 3.01 惩罚；总分来自最小 raw 其他维度。 |
| SMCI resolution 注入 AAPL | `68 / buy_candidate` | 5 | 与无当前事件的 AAPL 基线相同，不误伤也不奖励。 |

合成用例仍保留，但用途只限于无法安全在线制造的攻击边界，例如跨 CIK、同 URL 自引用、未来解决记录和伪造官方字段；它们不替代上述真实数据效果验证。

### 2026-07-14 真实运行数据契约复验

本轮不使用合成数据来宣称 fetch 层收益，而是直接调用项目 venv 中的当前数据源：

| 真实输入 | 修复前/风险 | 修复后硬边界 |
|---|---|---|
| `600519.SH` 东财现金流 | `NETCASH_OPERATE` 无法识别，OCF 静默为空 | 2026Q1 `269.1亿`只作最新披露；2025 年报 OCF `615.22亿` 只与 2025 净利计算 `0.75` |
| `688017.SH` 实时估值 | 缺行业时容易把跨行业参考解读为同行 | `industry_pe=—`；cninfo `33.2` 只是 market reference；DCF 明示标记净利代理输入 |
| `600519.SH` 基金持仓 | 环境变量可将几百家基金全部升级为网络富化 | 真实 `993` 源行/`671` 主动基金列表保留；完整统计默认上限 `50`，无界仅能显式 opt-in |
| `510300.SH` / `110011` | 证券类型错路由可重新触发成分股批量分析 | 实时识别 ETF/开放式基金并返回真实持仓；root pipeline 以无 traceback 的预期分流退回 legacy |

官方事件也以 `as_of=2026-07-14` 重抓 SMCI/HUBG/AAPL。新证据没有满足新事件族的终态门槛，因此不扩大解决态 taxonomy：SMCI Item 4.01 继续 unknown，HUBG Item 4.02/3.01 继续 active/unknown，AAPL 继续 gap。

最终报告为 `local-ops/state/branch-score-compare/20260714-live-data-contract-final.md`。baseline=`55580d0`，candidate=本轮代码树；`64 raw + 7 synthetic = 71`，分布为 core `10`、holdout `6`、official overlay `32`、synthetic raw `16`、synthetic feature `7`。结果 `71 ok / 0 review / 0 possible_regression`，评分和档位变化均为零。三轮纯评分中位数 `2.186s -> 2.177s`，无性能告警，只判定为持平。

### 2026-07-14 现金流量表 FCF 对比规则

DCF 输入效果必须与纯评分回归分开报告：

- fetch/估值收益使用当日真实现金流量表，在相同增长率和 WACC 下对比旧净利代理与新 FCF 输入。真实结果为 600519 `-11.3%`、688017 `-47.5%`、AAPL `+10.2%`；MSTR 保持 DCF 不适用。
- branch harness 仍只比较同一冻结 raw 输入上的纯评分与交易边界，不将网络数据随时间变化混入因果判断。
- 负 FCF 和零 FCF 是有效观测；不得过滤后回退到利润代理，不得用全零敏感度矩阵伪装可用估值。
- 报告必须同时展示 DCF 输入类型、期间、值、币种和警告；跨市场数值不得硬编码为人民币。

最终报告 `local-ops/state/branch-score-compare/20260714-real-fcf-final.md`：baseline=`f63f9b8`，`71 ok / 0 review / 0 possible_regression`，分数与档位变化为零。三轮纯评分中位数 `2.660s -> 2.607s`，无性能告警，只判定无回退。

### 在线、离线与 Agent 分工

最佳结构不是“来源越多越好”，而是“每个独立权威层至少一个稳定主源，镜像只增强溯源、不重复加权”：

| 层 | US | A 股 | 港股 | 进入评分的条件 |
|---|---|---|---|---|
| 发行人披露 | SEC 8-K | 巨潮公司公告 | HKEX issuer critical filings | 官方、精确实体、日期有效、taxonomy 明确 |
| 交易所 | SEC trading suspension 作为市场处置层 | SSE/SZSE 监管与纪律处分 | HKEX disciplinary action | 同上 |
| 监管执法 | SEC litigation releases | CSRC 行政处罚 | SFC enforcement | 同上；关联人默认 P2 |

- **必须在线**：发现最新处罚/公告、确认官方页面仍存在、读取当前日期和解决状态。这些事实会随时间变化，不能靠模型记忆。
- **必须离线确定性执行**：实体精确匹配、日期窗口、taxonomy、去重、严重度、评分、branch 对照。这样同一冻结输入跨 Windows/Mac 可复跑。
- **Agent/模型适合做**：发现候选官方入口、解释 P2 上下文、生成面向用户的说明、标记需要人工复核的冲突。
- **Agent/模型不得做**：凭常识补 P0/P1、把搜索摘要直接写入评分、猜测实体归属或解决状态。网络搜索只能用于发现，必须回到官方、可追溯、带日期的原文后再冻结。
- SEC 8-K 单源确实过窄，因此已补 SEC litigation releases 和 trading suspensions；A 股、港股也采用发行人、交易所、监管三层。公司 IR、媒体和搜索引擎可用于发现/解释，但不作为独立硬评分源，以免把转载数量误当事实强度。

## 性能与“卡壳”诊断

2026-07-09 复测发现，完整 branch-vs-branch harness 的等待感主要来自 A 股 lite 样本在 `generate_synthesis` 里的在线基金持仓 fallback，而不是美股/港股普遍慢：

- `600519.SH lite`：两个分支都约 80-90 秒。
- `688017.SH lite`：两个分支都约 50-60 秒。
- `00700.HK`、`AAPL`、`MSTR`、`CRCL`、`SIVE.ST`：通常约 0-1 秒。

这和早前 medium 跑出的 `859 fund/holding` 长循环不是同一个入口，但根因同属“评分/综合阶段不该触发基金持仓在线链路”：

- `859` 问题发生在采集/持仓枚举链路，属于 fetch 层性能问题。
- 本次卡壳发生在 `generate_synthesis -> detect_style -> detect_quant_signal -> fetch_holding_funds`。
- 二者都和 A 股基金/持仓源有关，但本次是在 branch harness 的“纯评分”阶段被意外触发。

已做的非破坏性 fix：

- 运行时打印分支级进度。
- 每个 raw/synthetic 样本打印开始/结束和耗时。
- raw 样本内部记录 `score_dimensions`、`generate_panel`、`generate_synthesis` 步骤耗时。
- Markdown/JSON 输出记录 baseline/candidate 行级耗时。
- 超过 30 秒的样本进入 `performance_warnings`，但不影响 `ok/review/possible_regression`。
- branch runner 设置 `UZI_SCORING_OFFLINE=1` / `UZI_QUANT_SIGNAL_OFFLINE=1`，并 monkeypatch 量化基金在线 fallback，使 branch 对照真正只使用缓存输入。
- `lib/quant_signal.py` 支持上述离线环境变量，避免纯评分场景偷偷访问 AkShare。

修复后完整 both+holdout 对照从数分钟级降到数秒级，并且 `29 ok / 2 review / 0 possible_regression` 不变。后续如果在非 harness 的普通报告流程中还遇到 859 长循环，应单独治理 fetch 层或 fund holdings runner，不要和评分公式质量问题混在一起。

## 2026-07-20 · 真实美股历史完整性影子

`tools/us_momentum_history_shadow.py` 补足了 branch harness 不覆盖 fetch 计算契约的盲区。它一次抓取 Yahoo 真实日线，在两个 detached worktree 中重放完全相同的 bars，并比较 60/90/120/180/200/full 窗口的 Stage、MA200 和年度窗口，不把在线漂移混入因果判断。

默认篮子为 `MU/WDC/STX/SNDK/GEV/BMNR/CRCL/FIG/SPCX`。2026-07-20 结果为 49 行：`42 beneficial_contract_fix / 7 no_change / 0 possible_regression`；31 轮纯计算中位 `0.092015s -> 0.087824s`，无性能告警。该工具只验证 fetch/指标证据完整性；评分和交易边界仍必须另跑 `branch_score_compare.py` 的 core、holdout、discovered cache、frozen overlays、synthetic adversarial 组合。本轮该组合为 `71/71` 且全部 score/tier delta 为 0。
