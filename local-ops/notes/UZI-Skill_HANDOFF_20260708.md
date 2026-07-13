# UZI-Skill 交接记录 - 2026-07-08

## 2026-07-13 最新状态

- 分支仍为 `codex/scoring-validation-guardrails`，个人远端为 `origin=https://github.com/hangfo/UZI-Skill.git`，upstream push 禁用。
- 结构化事件实现 commit：`418ae5b`；同步后应至少包含该 commit，最新文档 commit 以 `git log -1` 为准。
- branch-vs-branch、三市场官方事件 overlay、市场匹配反事实和结构化 P0/P1 消费契约均已完成。
- 最终 67 项对照：`61 ok / 6 review / 0 possible_regression`。
- `HUBG P0 -> AAPL`：`68/buy_candidate -> 59.9/watch`；`SMCI P1 -> AAPL`：`68/buy_candidate -> 64.9/watch`。
- 测试：branch harness `31/31`、builder `26/26`、scoring consistency `33/33`、`py_compile` 与 `git diff --check` 通过。
- 未重新安装、未跑 deep、未运行 update；branch runner 保持纯评分离线。
- 当前权重和事件阈值冻结。下一项是官方事件解决态的 shadow 验证，不再继续调分。

## 2026-07-08 历史起点

- 仓库：`D:\UZI-Skill`
- 分支：`codex/scoring-validation-guardrails`
- 交接时 HEAD：`5cf86467f72211c6337688aae0e9502a871c35aa`
- 远端：`origin/codex/scoring-validation-guardrails`
- 工作区：截至 2026-07-08 为 clean

## 已完成事项

已把 Replit HEAD 的评分修复导入 Windows，并额外加固边界测试。

相对 `codex/windows-local-stable` 的后续提交包括：

1. `dc3ef4c`：P0/P1/P2 评分修复与 score drift tracker。
2. `32a0bc2`：score drift schema 修复与评分一致性测试。
3. `59f3a53`：更完整的评分一致性测试与评分管道增强。
4. `5cf8646`：Windows 侧边界回归测试加固。

当前覆盖的关键行为：

- `recent_news` 是 canonical 字段。如果它存在但为空，不回退到过期旧字段 `news`。
- 严重负面事件即使只有一条，也可以压低事件分。
- 动态 `POLARIZE_K` 公式未改，但诊断现在暴露：
  - `polarize_stdev`
  - `polarize_active_count`
  - `polarize_skip_count`
- Stage 3 无价格测试现在检查真实护栏路径。
- 旧的固定 K 烟测现在验证动态 K 行为。
- Replit zip 附件噪声已从最终树移除。

## Windows 已完成验证

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

核心篮子：

| ticker | buy_score | 解读 |
|---|---:|---|
| AAPL | 68 | 质量强，估值受约束 |
| 600519.SH | 59 | 高质量，买点受约束 |
| 00700.HK | 59 | 高质量，趋势/回撤受约束 |
| MSTR | 34-36 | 风险/质量护栏生效 |
| AXTI | 32 | 投机小盘受约束 |

Holdout：

| ticker | buy_score | 解读 |
|---|---:|---|
| CRCL | 33-35 | 回避 |
| SIVE.ST | 36 | 回避 |
| 688017.SH | 55-58 | 谨慎观察 |

## Mac 同步提示词

在 Mac Codex App 中使用：

```text
Continue UZI-Skill. Sync remote branch:

origin/codex/scoring-validation-guardrails

If the branch does not exist locally:
git fetch origin codex/scoring-validation-guardrails
git checkout -b codex/scoring-validation-guardrails origin/codex/scoring-validation-guardrails

If it already exists locally:
git fetch origin
git checkout codex/scoring-validation-guardrails
git pull --ff-only

Do not reinstall. Do not run deep. Do not run update. Use the project local Python/venv.
After syncing, verify:
1. working tree clean
2. py_compile key scoring files
3. direct-run scoring consistency tests if pytest is unavailable
4. lite/medium regression basket
5. holdout CRCL, SIVE.ST, 688017.SH if cache exists

Expected branch state:
must contain commit 418ae5b; use git log -1 for the latest documentation commit
```

## 当前下一优先级

1. 对官方后续公告做 canonical event 生命周期关联，确定 `resolved/remediated/closed`，先只生成 overlay。
2. 用相同冻结输入离线复验解决态，确认解除风险不会误伤现有 P0/P1 结论。
3. NYSE/Nasdaq 动态列表没有稳定 schema 时保持 gap，不以搜索摘要或页面数量进入硬评分。
4. 按自然时间窗口积累 holdout，不围绕当前阈值挑样本。

推荐 GPT-5.6 medium；只有修改生命周期状态机或跨源 canonical matching 时使用 high。

## 2026-07-08 历史建议（已完成）

除非中立验证 harness 证明存在决策质量回退，否则不要继续调评分权重。

建议顺序：

1. 建立中立模型对比 harness：用同一批缓存 raw input，对比基线分支 `codex/windows-local-stable` 与当前分支 `codex/scoring-validation-guardrails`。
2. 扩展 holdout 覆盖：优先用 A/H/US/EU/JP/TW 的冻结缓存；缓存缺失时用小型 synthetic fixture。
3. 在测试后面设计数据质量系数，但在对照证明能改善决策行为前，不合入评分。
4. 评分验证稳定后，再改善 HTML 可读性。
5. 最后才考虑公式或权重调参。

## 下一轮边界规则

- 不重新安装。
- 除非明确要求，不跑 deep。
- 不运行 update 脚本。
- 保持 Windows/Mac 兼容。
- 新网络抓取前，优先使用缓存 raw data 和纯评分测试。
- 每次公式变更都需要：
  - 单调性测试
  - 对抗测试
  - branch-vs-branch 对照
  - lite/medium 篮子检查
  - holdout 检查
