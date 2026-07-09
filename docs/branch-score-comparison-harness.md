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

## 最新已知结果

扩展版运行结果：

```text
label: 20260708-expanded-core-holdout-both
result: 29 ok / 2 review / 0 possible_regression
```

输出文件：

```text
local-ops/state/branch-score-compare/20260708-expanded-core-holdout-both.md
local-ops/state/branch-score-compare/20260708-expanded-core-holdout-both.json
```

两个 `review` 都是预期内的风险收敛，不是公式回退：

- `high_quality_stage3_confirmed_downtrend`：`66.0 -> 59.0`，档位 `buy_candidate -> watch`。
- `stage4_missing_price_high_quality`：`66.0 -> 59.0`，档位 `buy_candidate -> watch`。

这两个变化说明候选分支阻止了 Stage 3/4 下的质量保底误触发买入信号。

Synthetic raw-data 检查也显示字段契约符合预期：

- 空 `recent_news` + 旧 `news`：基线 `15_events=8`，候选分支 `15_events=5`。
- 单条强负面事件：基线 `15_events=5`，候选分支 `15_events=4`。
- 否定负面事件：基线 `15_events=5`，候选分支 `15_events=5`。
- 财务缺失 raw 样本：候选分支保持 `cautious`，没有变成买入。

以后如果出现非零 `possible_regression`，先检查具体样本证据，再决定是否修改评分公式。
