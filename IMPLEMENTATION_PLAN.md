# UZI-Skill 评分引擎改造计划

> 本文档列出所有待执行改动，按 P0→P1→P2→巧思 排序。
> 完成后将写入 `PROJECT_SUMMARY.md` 记录实际 diff。

---

## P0：静默 bug（零风险，高影响，立即修复）

### P0-A　Feature key 错位 → 成长派评委永远判 0%

**文件**：`skills/deep-analysis/scripts/lib/stock_features.py`

| 规则引用 key | `extract_features()` 实际 key |
|---|---|
| `rev_growth_3y` | `revenue_growth_3y_cagr` |
| `rev_growth_yoy` | `revenue_growth_latest` |

成长派（Lynch / Wood / Tiel 等 B/H 组）所有含 `rev_growth_3y` 的规则永远取 0，
导致成长型股票被系统性压分。PEG = PE / 0 = 99，所有 PEG 规则判"贵"。

**修复**：在 `extract_features()` 末尾追加别名映射：
```python
# Key alias bridge — 兼容 investor_criteria 旧 key 名
f["rev_growth_3y"]  = f.get("revenue_growth_3y_cagr", 0)
f["rev_growth_yoy"] = f.get("revenue_growth_latest", 0)
```

---

### P0-B　dim_15 字段名错位 → 事件维度永远 5 分

**文件**：`skills/deep-analysis/scripts/lib/pipeline/score_fns.py`，约第 218 行

`score_dimensions()` 读 `events.get("news")`，但 fetcher 写入 `recent_news`。
即使拉到 50 条新闻，事件维度（权重 4）每只股票都是 5 分。

**修复**：
```python
# before
news = events.get("news") or []
# after
news = events.get("news") or events.get("recent_news") or []
notices = events.get("recent_notices") or notices  # 同步补充 notices fallback
```

---

### P0-C　falling_trend_cap 遗漏 Stage 3

**文件**：`skills/deep-analysis/scripts/lib/pipeline/score_fns.py`

Stage 3（Wyckoff 分配/出货）与 Stage 4 同样危险，但 cap 只在 `stage_num == 4` 触发。
高质量 Stage 3 股票仍能触发 `quality_floor` 保底 → 误发"可以蹲一蹲"买入信号。

**修复**：
```python
# before
if stage_num == 4:
# after
if stage_num in (3, 4):
```
附加：Stage 3 价格确认条件（ytd ≤ -10% 或 max_dd ≤ -25%），避免 Stage 3 早期误判。

---

## P1：系统性偏差（需回归验证，影响 fundamental_score 区分度）

### P1-A　6 个硬编码 stub 维度修复

**文件**：`skills/deep-analysis/scripts/lib/pipeline/score_fns.py`，`score_dimensions()` 函数

| 维度 | 当前 | 改为 |
|---|---|---|
| `14_moat` | 固定 6 | 读 `moat.scores` 四项之和映射 1-10 |
| `3_macro` | 固定 6 | 读 `rate_cycle` / `geo_risk` 关键词打分 |
| `7_industry` | 固定 7 | 读 `industry.growth` 数值/正负趋势打分 |
| `13_policy` | 固定 6 | 读 `policy_dir` 字段（积极/收紧/中性） |
| `8_materials` | 固定 6 | 数据缺口：改为标注 `_data_gap: True`，仍输出 6 |
| `9_futures` | 固定 5 | 数据缺口：改为标注 `_data_gap: True`，仍输出 5 |

---

### P1-B　LHB 改用净流向而非上榜次数

**文件**：`skills/deep-analysis/scripts/lib/pipeline/score_fns.py`

当前：龙虎榜出现次数越多分越高（正向无条件）。
改为：读 `inst_vs_youzi.institutional_net` 净流入为正则加分，游资净主导则减分。

---

### P1-C　事件维度加情感过滤

**文件**：`skills/deep-analysis/scripts/lib/pipeline/score_fns.py`

负面新闻关键词（暴雷 / 违规 / 处罚 / 退市 / fraud / lawsuit / SEC / recall）出现
→ 该条新闻计为 -0.5 而非 +1，极端负面事件直接压低 dim_15。

---

## P2：模型结构优化（全局影响，需完整回归）

### P2-A　权重重新校准

**文件**：`skills/deep-analysis/scripts/lib/pipeline/score_fns.py`，`compute_investment_score()`

| 维度 | 当前 | 改为 |
|---|---|---|
| `quality_weight` | 0.25 | **0.30** |
| `catalyst_weight` | 0.28 | **0.22** |

其余轴不变，合计保持 1.0。

---

### P2-B　POLARIZE_K 动态自适应

**文件**：`skills/deep-analysis/scripts/lib/pipeline/score_fns.py`，`generate_panel()`

当前：`POLARIZE_K = 1.30` 固定常数。
改为：根据 active 评委分数的标准差动态计算：
```python
stdev = statistics.stdev(active_scores) if len(active_scores) > 1 else 10
POLARIZE_K = max(1.10, min(1.50, 1.30 * (10 / max(stdev, 1))))
```
分歧大（stdev 高）时少拉，分歧小时多拉。

---

## 巧思：评分漂移检测（Score Drift Tracker）

**新文件**：`skills/deep-analysis/scripts/lib/pipeline/score_drift.py`
**修改**：`run.py` 在 `--score-drift` flag 下调用 drift reporter

每次评分完成后，将三轨分数追加到 `.cache/_global/score_history.jsonl`：
```json
{"ts": "2026-07-06T12:00:00", "ticker": "AAPL", "market": "US",
 "overall": 71, "buy_score": 68, "fundamental": 74,
 "panel_mean": 66.2, "active_count": 42}
```

`python run.py --score-drift AAPL` 读取历史，打印：
- 三轨分数时序变化表
- 标注每次 ≥3 分波动并说明可能原因（维度变化 / 评委新增 / 权重调整）

---

## 实施顺序

```
P0-A → P0-B → P0-C   # 零风险，先上
P1-A (moat+macro+industry+policy)  # 有实际数据驱动
P1-B (LHB 净流向)
P1-C (事件情感)
P2-A (权重)  →  P2-B (动态 K)
巧思 (drift tracker)
```

每步完成后运行现有测试套件（`pytest skills/deep-analysis/scripts/tests/`）验证回归基线不破坏。
