# UZI-Skill 评分引擎改造项目摘要

> 来源分支：`hangfo/UZI-Skill` · `codex/windows-local-stable`
> 改造日期：2026-07-06
> 改造范围：评分管道 P0 静默 bug 修复 + P1 系统性偏差 + P2 模型优化 + 巧思新功能

---

## 当前事实源

- 文档中文化与治理准则：`docs/documentation-governance.md`
- 分支评分对照 harness：`docs/branch-score-comparison-harness.md`
- 评分模型回归验证计划：`docs/scoring-model-regression-plan.md`
- Windows 后续验证记录：`SCORING_WINDOWS_FOLLOWUP_20260707.md`
- 本地交接记录：`local-ops/notes/UZI-Skill_HANDOFF_20260708.md`
- 历史文档归档：`docs/archive/README.md`

当前原则：评分公式先冻结；先用同一批缓存 raw data 做旧分支 vs 新分支的中立对照。英文入口、agent 指令、命令模板和 schema 契约不做机械翻译，避免改变工具行为。

截至 2026-07-13，branch-vs-branch 已证明结构化官方负面事件存在明确交易决策问题，因此只增加了最小事件风险消费契约，没有继续调权重。最终 67 项对照为 `61 ok / 6 review / 0 possible_regression`；结构化 P1 处理能力从 `4.0/10` 提升到 `8.8/10`。在线官方事实先冻结为 overlay，实体匹配、时效、去重、严重度和评分全部离线确定性执行。

截至 2026-07-29，US entity shadow 已用三批共 349 条真实 Yahoo 新闻验证，候选为 precision `100%`、recall `99.40%`、跨发行人污染 `0`；AAL 生产审计进一步修复法人名行业通用词污染。正式分支对候选的 99 项冻结比较为 `99 ok / 0 possible_regression`，评分和交易档位全为零变化。37 股 10 年真实 walk-forward 不支持增加动量权重，Stage 只保留为风险护栏；当前热门 8 股压力样本因选择偏差不用于调参。
同日后续治理把 SEC 官方 overlay 改为默认离线、真实联系人显式 opt-in，并保持
CBOE 零联网；当前无真实 SEC 身份，因而保留 access gap。真实 INTC/SOFI 发现
yfinance 日线尾部落后一个交易日，现只用 Yahoo v8 五日尾部追加严格更新日期；
105 项冻结对照为 `105 ok / 0 possible_regression`，评分/档位同输入零变化。
新增 8 股 1045 信号压力回测仍不支持提高动量权重。

---

## 改动总览

| 类别 | 项目 | 文件 | 状态 |
|---|---|---|---|
| P0 | Feature key 错位（成长派永远 0 分） | `stock_features.py` | ✅ 已修复 |
| P0 | PEG 计算用了未赋值 key | `stock_features.py` | ✅ 已修复 |
| P0 | dim_15 事件维度字段名错位 | `score_fns.py` | ✅ 已修复 |
| P0 | falling_trend_cap 遗漏 Stage 3 | `score_fns.py` | ✅ 已修复 |
| P1 | dim_3 宏观：硬编码 6 → 读 rate_cycle / geo_risk | `score_fns.py` | ✅ 已修复 |
| P1 | dim_7 行业景气：硬编码 7 → 读 growth 字段 | `score_fns.py` | ✅ 已修复 |
| P1 | dim_13 政策：硬编码 6 → 读 policy_dir 情感 | `score_fns.py` | ✅ 已修复 |
| P1 | dim_14 护城河：硬编码 6 → 读 scores 四力 | `score_fns.py` | ✅ 已修复 |
| P1 | dim_15 事件：加负面新闻情感折扣 | `score_fns.py` | ✅ 已修复 |
| P1 | 官方结构化 P0/P1：精确实体/时效/解决态消费与买入护栏 | `score_fns.py` | ✅ 已修复并完成三市场对照 |
| P1 | dim_16 龙虎榜：改用净流向（inst_vs_youzi） | `score_fns.py` | ✅ 已修复 |
| P2 | Quality 权重 0.25→0.30，Catalyst 0.28→0.22 | `score_fns.py` | ✅ 已修复 |
| P2 | POLARIZE_K 改为动态自适应（基于 stdev） | `score_fns.py` | ✅ 已修复 |
| 巧思 | 评分漂移追踪器（score_drift.py） | 新文件 | ✅ 已新增 |
| 巧思 | `--score-drift` CLI flag | `run.py` | ✅ 已新增 |
| 工具 | US/A/HK 官方负面事件 overlay + branch counterfactual | `evidence_overlay_builder.py` / `branch_score_compare.py` | ✅ 已完成 |

---

## P0 修复详情

### P0-A：Feature key 错位（stock_features.py）

**问题**：`investor_criteria.py` 中大量规则引用 `rev_growth_3y` / `rev_growth_yoy`，但 `extract_features()` 输出的是 `revenue_growth_3y_cagr` / `revenue_growth_latest`。导致 Lynch / Wood / Tiel 等 B/H 组成长派规则永远取 0，成长股被系统性压分。PEG 也因此变为 PE/0 = 99，所有 PEG 规则判"太贵"。

**修复 diff（概要）**：
```diff
- peg_val = f.get("pe", 0) / f.get("rev_growth_3y", 1) if f.get("rev_growth_3y", 0) > 0 else 99
+ _peg_growth = f.get("revenue_growth_3y_cagr", 0)
+ peg_val = f.get("pe", 0) / _peg_growth if _peg_growth > 0 else 99

+ # Key alias bridge — 让 investor_criteria 旧 key 正常取值
+ def extract_features(raw, dims=None):
+     f = _original_extract_features(raw, dims)
+     f["rev_growth_3y"]  = f.get("revenue_growth_3y_cagr", 0)
+     f["rev_growth_yoy"] = f.get("revenue_growth_latest", 0)
+     return f
```

**受益评委**：B 组（Lynch/Wood/Tiel）、H 组（科技领袖）、G 组量化规则中的成长因子。

---

### P0-B：dim_15 事件维度字段名错位（score_fns.py）

**问题**：`score_dimensions()` 读 `events.get("news")`，而 fetcher 实际写入 `recent_news`。即使拉取 50 条新闻，事件维度每只股票都得同样的 5/10 分。

**修复 diff（概要）**：
```diff
- news = events.get("news") or []
+ news = events.get("news") or events.get("recent_news") or []
```

---

### P0-C：falling_trend_cap 遗漏 Stage 3（score_fns.py）

**问题**：`falling_trend_cap` 只在 `stage_num == 4` 触发。Wyckoff Stage 3（分配/出货）同样危险，但高质量 Stage 3 股票仍能触发 `quality_floor` → 误发"可以蹲一蹲"买入信号。

**修复 diff（概要）**：
```diff
- falling_trend_cap = stage_num == 4 and (ytd <= -10 or max_dd <= -25)
+ falling_trend_cap = stage_num in (3, 4) and (ytd <= -10 or max_dd <= -25)
```

---

## P1 修复详情

### P1-A：4 个硬编码 stub 维度修复（score_fns.py）

以下 4 个维度原先对所有股票返回同一常数分，现改为读取实际数据：

| 维度 | 原来 | 现在 |
|---|---|---|
| **3_macro** | 硬编码 6 | 读 `rate_cycle`（降息+1 / 加息-1）+ `geo_risk`（低+1 / 高-1） |
| **7_industry** | 硬编码 7 | 读 `growth` 字段：数值优先，否则关键词匹配（高景气=9 / 衰退=3） |
| **13_policy** | 硬编码 6 | 读 `snippets.policy_dir`：积极/利好=8 / 收紧/利空=3 / 中性=5 |
| **14_moat** | 硬编码 6 | 读 `scores{intangible/switching/network/scale}` 四力之和 / 4，无数据标注 `_data_gap` |

剩余 2 个 stub（8_materials / 9_futures）无结构化数据源，保持原分并已标注 `_data_gap: True`。

---

### P1-B：dim_16 龙虎榜改用净流向（score_fns.py）

**问题**：上榜次数越多分越高，游资操纵股因高频出现反而得高分。

**修复**：优先读 `inst_vs_youzi.institutional_net` 净流入方向打分；无净流向数据时 fallback 到收窄的次数打分（上限 +2 而非 +3）。

```diff
- score_16 = 5 + min(3, lhb_count // 2)
+ if inst_vs:
+     score_16 = 5
+     if inst_net > 0: score_16 += 3        # 机构净买入 → 正信号
+     elif inst_net < 0 and youzi_net > 0: score_16 -= 1  # 游资买机构撤
+ else:
+     score_16 = 5 + min(2, lhb_count // 3)  # 纯次数：收窄上限
```

---

### P1-C：dim_15 事件加负面情感折扣（score_fns.py）

负面新闻关键词（暴雷 / 违规 / 处罚 / 退市 / fraud / lawsuit 等）的条目计为 -0.5 权重，而非正常的 +1。防止"大量负面新闻 → 高事件分"的悖论。

---

## P2 修复详情

### P2-A：权重重新校准（score_fns.py）

| 轴 | 原权重 | 新权重 |
|---|---|---|
| quality | 0.25 | **0.30** |
| growth | 0.17 | 0.17 |
| catalyst | 0.28 | **0.22** |
| valuation | 0.15 | 0.15 |
| risk_control | 0.15 | **0.16** |
| **合计** | 1.00 | 1.00 |

质量轴（公司基本面）现超过题材轴（AI 叙事/催化剂），减少"讲故事 > 实际质量"的定价偏差。

---

### P2-B：POLARIZE_K 动态自适应（score_fns.py）

**原来**：`POLARIZE_K = 1.30`（常数，不管评委分歧大小）

**现在**：基于当次 active 评委分布的标准差动态计算：
```python
stdev = statistics.stdev(active_scores)
POLARIZE_K = max(1.10, min(1.50, 1.30 * (10 / max(stdev, 1))))
```
- stdev ≈ 10（基准）→ K = 1.30 不变
- stdev ≈ 5（分歧小，共识强）→ K ≈ 1.50（拉开更多）
- stdev ≈ 20（分歧大，意见分裂）→ K ≈ 1.10（保守，减少失真）

---

## 巧思：评分漂移追踪器

### 新文件：`skills/deep-analysis/scripts/lib/pipeline/score_drift.py`

每次 `run.py` 分析完成后，三轨分数（overall / buy_score / fundamental / panel_consensus）自动追加到 `.cache/_global/score_history.jsonl`。

### CLI 用法

```bash
python run.py AAPL --score-drift       # 打印历史漂移表，不重新分析
python run.py 600519.SH --score-drift  # 同上，适用 A 股
```

### 输出示例

```
══════════════════════════════════════════════════════════════════════
📊 评分漂移报告：AAPL  (3 次记录)
══════════════════════════════════════════════════════════════════════
时间 (UTC)            overall    buy_score    fundamental    panel   K
----------------------------------------------------------------------
2026-07-04 09:12:00   68.0       66.5         71.2          63.4    1.28
2026-07-05 14:30:00   68.0       67.1         71.2          63.9    1.31
2026-07-06 10:15:00   71.0       70.3 ▲3.2⚠   74.0 ▲2.8⚠   66.1    1.25

  overall 最大漂移 = 3.0 分 | 最新 = 71.0 | 首次 = 68.0
```

漂移 ≥ 3 分时自动标注 `⚠`；漂移 ≥ 5 分时打印建议检查方向。

---

## 文件变更汇总

| 文件 | 操作 | 主要改动 |
|---|---|---|
| `skills/deep-analysis/scripts/lib/stock_features.py` | 修改 | PEG key 修复；`extract_features` wrapper + 别名桥 |
| `skills/deep-analysis/scripts/lib/pipeline/score_fns.py` | 修改 | dim_3/7/13/14/15/16 实数据化；falling_trend_cap Stage 3；权重重校；动态 POLARIZE_K |
| `skills/deep-analysis/scripts/lib/pipeline/score_drift.py` | **新增** | 评分漂移追踪器（record + report） |
| `run.py` | 修改 | `--score-drift` flag；分析完成后自动追加漂移记录 |

---

## 回归基线影响预测

| 股票 | 预测方向 | 原因 |
|---|---|---|
| AAPL | overall +2~5 | 成长派规则修复（rev_growth 恢复）+ 护城河实分（高 moat_total） |
| 600519.SH | overall ±2 | 政策利好可能 +1；护城河实分高；Stage 2 无 cap 影响 |
| 00700.HK | overall ±1 | 护城河实分；事件修复后若有负面新闻略降 |
| MSTR | overall -2~4 | Catalyst 权重降低；Stage 3/4 cap 覆盖面扩大 |
| AXTI | overall -3~5 | Stage 3 cap 现在生效；成长规则修复后 B/H 组可能更看多（抵消部分） |
