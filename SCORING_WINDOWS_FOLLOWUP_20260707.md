# 评分 Windows 跟进记录 - 2026-07-07

本记录说明：把 Replit HEAD 的评分修复导入 `codex/scoring-validation-guardrails` 后，在 Windows 侧做了额外边界加固。

## 额外边界修复

1. `15_events.recent_news` 现在被视为 canonical 字段。只要 `recent_news` 存在，即使是空列表 `[]`，也不再回退到旧字段 `news`，避免过期缓存新闻被当作新证据。
2. 事件情绪现在允许少量严重负面事件把分数压到中性以下。欺诈、财务造假、SEC 指控、立案调查等信号，应当影响买卖判断，而不是必须重复出现十次才生效。事件总惩罚仍封顶 3 分。
3. `consensus_formula` 现在暴露：
   - `polarize_stdev`
   - `polarize_active_count`
   - `polarize_skip_count`

   动态 `POLARIZE_K` 公式未改；这里仅增强漂移可观测性。
4. 测试已收紧，改为检查真实输出路径和当前动态 K 行为，而不是检查过期假设。

## 新增或加强的测试

- `test_p0b_empty_recent_news_does_not_fallback_to_stale_news`
- `test_p1c_genuine_negative_events_penalised` 从 `<= 5` 收紧到 `< 5`
- `test_p1c_single_strong_negative_event_penalised`
- `test_p2b_polarize_diagnostics_present`
- Stage 3 无价格测试现在读取 `diagnostics.guardrails.falling_trend_cap`
- v2.15.4 流派分烟测现在接受动态 K，并检查诊断字段

## Windows 验证

- `py_compile`：通过
- `test_scoring_consistency.py` direct harness：26 passed，0 failed
- `test_v2_15_4_school_scores.py` direct harness：9 passed，0 failed
- `local-ops/tools/scoring_regression_basket.py`：通过

对抗探针：

| case | dim_15 score |
|---|---:|
| 两条强负面事件 | 4 |
| 单条强负面事件 | 4 |
| canonical news 为空但旧 news 有过期内容 | 5 |
| 20 条正面 canonical news | 7 |
| 否定负面语境 | 5 |

核心篮子快照：

| mode | ticker | overall | investment_score | 解读 |
|---|---:|---:|---:|---|
| lite | 600519.SH | 51.9 | 59.0 | 高质量，但买点受约束 |
| lite | 00700.HK | 51.0 | 59.0 | 高质量，但趋势/回撤受约束 |
| lite | AAPL | 49.9 | 68.0 | 质量被识别，估值受约束 |
| lite | MSTR | 38.0 | 34.3 | 质量/风险护栏生效 |
| lite | AXTI | 43.8 | 31.9 | 投机小盘风险受约束 |

Holdout 快照：

| mode | ticker | overall | investment_score | 解读 |
|---|---:|---:|---:|---|
| lite | CRCL | 41.1 | 33.3 | 回避；下跌趋势护栏生效 |
| lite | SIVE.ST | 47.2 | 36.3 | 回避；亏损/高估值护栏生效 |
| lite | 688017.SH | 54.8 | 54.9 | 谨慎；增长高但估值轴只有 20 |
| medium | CRCL | 40.9 | 34.5 | 回避；结论稳定 |
| medium | SIVE.ST | 47.2 | 36.3 | 回避；结论稳定 |
| medium | 688017.SH | 56.6 | 57.8 | 谨慎；没有被成长叙事过度推高 |
