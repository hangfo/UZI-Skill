# 文档中文化与治理准则

日期：2026-07-09

## 目标

本仓库需要让中文用户可以顺畅接手评分验证、分支对照和本地运行，但不能因为机械翻译破坏 agent 指令、命令入口、schema 字段或跨平台约定。

因此，中文化的目标不是“把所有英文字符改成中文”，而是：

- 面向用户、交接和验证结论的文档，优先中文化。
- 面向 agent、插件、命令和协议的文档，保持原语义稳定。
- 代码块、CLI 参数、环境变量、JSON key、文件路径、分支名和测试标签不翻译。
- 历史记录、第三方模板、英文入口文档，除非有明确维护需求，不做机械翻译。

## 当前结论

### 已优先中文化

这些文件承载当前评分验证事实源，适合中文维护：

- `docs/branch-score-comparison-harness.md`
- `docs/scoring-model-regression-plan.md`
- `SCORING_WINDOWS_FOLLOWUP_20260707.md`
- `local-ops/notes/UZI-Skill_HANDOFF_20260708.md`
- `local-ops/state/branch-score-compare/*.md`

### 保持原语义，不做机械翻译

这些文件会影响 agent 或工具行为，后续如需修改，应按“语义审查”处理，而不是批量翻译：

- `AGENTS.md`
- `CODEX.md`
- `GEMINI.md`
- `SKILL.md`
- `skills/*/SKILL.md`
- `commands/*.md`
- `hooks/README.md`
- `.codex/INSTALL.md`
- `.opencode/INSTALL.md`
- `skills/deep-analysis/assets/data-contracts.md`

原因是这些文件包含入口命令、硬门槛、角色约束、字段契约或插件安装约定。翻译措辞可能改变 agent 对“必须做什么”的判断。

### 保留英文入口或第三方模板

这些文件本身就是英文入口、社区模板或合规文本，不建议为了中文化而改写：

- `README_EN.md`
- `CODE_OF_CONDUCT.md`
- `.github/ISSUE_TEMPLATE/*.md`

如果需要中文说明，应新增中文入口或在中文主文档中指向它们，而不是改写英文版。

### 可后续定向治理

这些文件不是当前评分公式的控制面，但含有较多历史说明、数据源说明或测试计划。建议在确认仍被使用后，再逐份中文化或归档：

- `docs/DATA-PROVIDERS.md`
- `docs/TEST-PLAN-v2.10.3.md`
- `docs/BUGS-LOG.md`
- `PROJECT_SUMMARY.md`
- `INSTALL-HERMES.md`

### 已归档历史文档

这些文件保留追溯价值，但不再作为当前开发入口：

- `docs/archive/PROJECT-SUMMARY-20260701.md`
- `docs/archive/SCORING_IMPLEMENTATION_PLAN_20260706.md`
- `docs/archive/CHANGELOG-LOCAL-20260629-20260701.md`

## 修改守则

1. 先判定文档角色，再决定是否中文化。
2. 如果文档被 agent、插件、harness 或测试读取，优先保持命令、字段、标题锚点和示例结构稳定。
3. 如果要翻译底层规范文档，必须逐段确认“翻译后不会改变约束强度”。
4. 如果只是为了中文可读性，优先补充中文摘要或治理索引，不直接改写英文事实源。
5. 每次文档治理后至少运行 `git diff --check`，避免 Markdown 空白和编码问题。

## 下一步建议

评分公式继续冻结。下一步优先做文档事实源收敛：

1. 继续保持 `PROJECT_SUMMARY.md` 作为当前项目摘要，不再恢复根目录 `PROJECT-SUMMARY.md`。
2. `docs/DATA-PROVIDERS.md` 只作为数据缺口排查参考，不作为当前安装计划。
3. `docs/TEST-PLAN-v2.10.3.md` 只作为历史测试方案，不作为当前执行计划。
4. 文档事实源收敛后，继续扩大 branch-vs-branch harness 的样本和阈值解释，而不是调评分公式。
