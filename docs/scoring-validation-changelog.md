# Scoring Validation 变更日志

> 当前文档记录 `codex/scoring-validation-guardrails` 分支上的评分验证、branch-vs-branch harness、证据冻结与文档治理改动。它是开发追溯文档，不是 agent 指令入口；影响 agent 行为的规则仍以 `AGENTS.md` 和相关 harness 文档为准。

## 2026-07-09

### 本轮 · Frozen overlay 接入 branch harness

- 在 `tools/branch_score_compare.py` 中新增 `--include-evidence-overlays` 和 `--overlay-dir`。
- `status=ready` 的 `negative_event` overlay 会被转换为 raw-data 同链路样本，进入 baseline/candidate 对照。
- `gap`、`partial`、schema 不匹配、缺少 `title/url/severity` 的 overlay 不进入对照。
- overlay 证据类型标记为 `frozen_overlay`，不冒充真实缓存或 synthetic。
- 增加 P0/P1/P2 的对照边界：
  - `P0`：事件维度必须低于中性，并限制总分。
  - `P1`：限制高置信买入，但不强制事件维度低于中性。
  - `P2`：只作为 review 证据。
- 增加中文展示层：overlay 保持英文 schema 和机器枚举，同时输出 `display`、`label_zh`、`severity_label_zh`，方便前端中文展示。
- Overlay-backed 复验结果：`31 ok / 2 review / 0 possible_regression`。

### `bc9d010` · SEC 负面事件 overlay adapter

- 在 `tools/evidence_overlay_builder.py` 中为 `negative_event` 增加美股 SEC submissions adapter。
- 用 SEC 8-K item code 定义负面事件优先级：
  - `P0`：破产/接管、财报不可依赖等硬风险。
  - `P1`：重大网络安全、债务触发、重大减值、退市通知、审计师变更等重大风险升级。
  - `P2`：需要上下文的经营或法律风险。
- 增加 SMCI 真实在线验证：SEC 8-K Item `3.01` 命中 `P1`，生成 `ready/high` overlay。
- 增加 AAPL 反例验证：无 P0/P1 证据时保持 `gap/low`，不误报负面事件。
- 新增 8 个 overlay builder 测试，覆盖 SEC item taxonomy、否定语义、缺证据 gap、机器枚举不被中文展示层破坏。

### `44ebc34` · 冻结证据 overlay 构建器

- 新增 `tools/evidence_overlay_builder.py`，把在线或缓存事实冻结为 `uzi.evidence_overlay.v1`。
- 支持 `missing_financials` 的美股 SEC `companyfacts` 字段映射。
- 支持 `negative_event` 的本地缓存证据冻结；当没有官方 adapter 或证据不足时保持 `gap`。
- 默认写入 `local-ops/state/evidence-overlays/<ticker>-<target>.json`，不直接参与评分。
- 增加 `--no-network` 和 `--no-write`，便于离线测试和只读验证。
- 真实在线验证：`AAPL missing_financials -> ready / high confidence / ~5.8s`。

### `597119e` · 真实缓存补盲审计

- 在 `tools/branch_score_compare.py` 增加 `--audit-cache-blindspots`。
- 增加四类真实缓存覆盖目标：
  - `negative_event`
  - `missing_financials`
  - `stage3_4`
  - `lhb_activity`
- 审计结果显示：
  - `negative_event`：真实缓存覆盖 `0/2`，仍是高优先级缺口。
  - `missing_financials`：真实缓存覆盖 `0/2`，仍是高优先级缺口。
  - `stage3_4`：真实缓存覆盖 `4/4`，市场覆盖 `3/3`，已满足。
  - `lhb_activity`：真实缓存覆盖 `2/1`，已满足。
- 明确 synthetic 样本不能冒充真实缓存覆盖。
- 输出在线补证据计划：官方来源优先、先冻结 overlay、再进入离线对照。

### `6fddf9d` · branch harness 离线化与性能可见性

- branch runner 设置 `UZI_SCORING_OFFLINE=1` 和 `UZI_QUANT_SIGNAL_OFFLINE=1`。
- 避免 branch-vs-branch 对照过程中触发 A 股基金持仓在线 fallback。
- 增加分支级、样本级、步骤级耗时输出。
- 增加 `performance_warnings`，超过阈值只提示，不改变 `ok/review/possible_regression`。
- 完整 both+holdout 对照从分钟级降到数秒级。

### `7e5c019`、`9c202ad`、`ffb3980` · 解释性、交叉支持与可靠性

- 为每行比较增加稳定归因、置信度、边界余量、阈值敏感性和主要轴向变化。
- 增加交叉支持层，区分真实缓存、synthetic raw、synthetic feature 等证据来源。
- 增加可靠性层，综合单行置信度、交叉支持和边界敏感性。
- 明确 `review` 不等于回退，只有违反硬边界才进入 `possible_regression`。

### `c66d680`、`48da79e`、`179cd5b` · 中文文档治理

- 将当前评分验证相关文档改为中文优先。
- 归档过期规划文档，避免影响后续开发计划。
- 保留基础规范、agent 指令、历史入口等不适合翻译或不应改动的内容。

## 2026-07-08

### `a594ff5` · 扩展对抗样本与数据质量边界

- 扩展 branch-vs-branch harness 的 core、holdout、synthetic feature、synthetic raw-data 样本。
- 增加 Stage 3/4、财务缺失、单条强负面事件、否定负面事件等对抗边界。
- 验证候选分支没有把风险样本推成买入，也没有把质量控制样本误降到边界以下。

### `646fa9a` · branch-vs-branch comparison harness

- 新增 `tools/branch_score_compare.py`，用同一批缓存 raw data 对比 `codex/windows-local-stable` 与 `codex/scoring-validation-guardrails`。
- 目标是先中立比较旧分支 vs 新分支的买卖决策是否回退，而不是继续调评分公式。
- 输出 `ok/review/possible_regression` 三类判定。
- 支持 core basket、holdout、synthetic cases。

### `977bc3d` · repo-local handoff 与进度持久化

- 持久化 UZI scoring-validation 交接文档和进度日志。
- 明确边界：不重新安装、不跑 deep、不运行 update、优先缓存 raw data 和纯评分函数。
- 保证后续 session 或 Mac 同步时有可读入口。

## 后续计划

1. 把 `status=ready` 的 frozen overlay 通过显式开关接入 branch harness。
2. 用 overlay-backed holdout 验证真实官方负面事件是否影响 `15_events` 和最终买卖档位。
3. 继续扩展官方结构化 adapter，而不是按个股或新闻站点零散接入：
   - A 股：巨潮公告、交易所纪律处分、证监会处罚。
   - 港股：HKEXnews、SFC enforcement。
4. 保持评分公式冻结；只有 neutral branch comparison 证明存在明确交易决策问题时，才讨论公式修改。
