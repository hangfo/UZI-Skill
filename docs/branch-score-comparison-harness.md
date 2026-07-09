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

## 最新已知结果

扩展版运行结果：

```text
label: 20260709-cross-support-core-holdout-both
result: 29 ok / 2 review / 0 possible_regression
```

输出文件：

```text
local-ops/state/branch-score-compare/20260709-cross-support-core-holdout-both.md
local-ops/state/branch-score-compare/20260709-cross-support-core-holdout-both.json
```

两个 `review` 都是预期内的风险收敛，不是公式回退：

- `high_quality_stage3_confirmed_downtrend`：`66.0 -> 59.0`，档位 `buy_candidate -> watch`，归因为 `trend_guardrail_tightening`，置信度 `high(82)`，交叉支持 `limited`。
- `stage4_missing_price_high_quality`：`66.0 -> 59.0`，档位 `buy_candidate -> watch`，归因为 `trend_guardrail_tightening`，置信度 `medium(64)`，交叉支持 `limited`；因为候选分数贴近上限边界，仍需人工复核但不判回退。

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
