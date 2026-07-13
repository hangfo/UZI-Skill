# Scoring Validation 变更日志

> 当前文档记录 `codex/scoring-validation-guardrails` 分支上的评分验证、branch-vs-branch harness、证据冻结与文档治理改动。它是开发追溯文档，不是 agent 指令入口；影响 agent 行为的规则仍以 `AGENTS.md` 和相关 harness 文档为准。

## 2026-07-13

### 三市场官方负面事件 adapters 与反事实对照

- `tools/evidence_overlay_builder.py` 新增 A/HK 官方 adapter：
  - 巨潮：动态读取 `orgId`，按证券代码查询公司公告。
  - 上交所：按证券代码查询监管措施/纪律处分官方接口。
  - 深交所：接入监管措施和纪律处分两个官方 report catalog。
  - HKEX：从 disciplinary overview 精确提取 `Stock Code`。
  - SFC：读取 enforcement 列表与正文，只有正文精确 stock code 匹配才归属公司。
- 保留并复验美股 SEC submissions adapter，形成 US/A/HK 同一 overlay schema。
- 增加统一 guardrails：
  - 默认 730 天时效窗口；边界日计入，未来/无日期证据剔除。
  - 官方域名 + 精确实体匹配 + P0/P1 才能生成 `ready`。
  - 前董事/前主席等关联人事件降为 P2，不能单独进入 branch 对照。
  - 问询函、关注函、回复函、监管工作函不自动认定为处罚。
  - 巨潮镜像与交易所原文合并，保留 corroborating provenance，不重复加权。
- `tools/branch_score_compare.py` 增加市场匹配反事实样本：
  - US overlay 注入 AAPL 缓存。
  - A 股 overlay 注入 600519.SH 缓存。
  - HK overlay 注入 00700.HK 缓存。
  - 反事实只追加事件字段，其余 raw data 不变，并明确标记，不冒充真实归属。
- 真实冻结样本：
  - `SMCI`、`002038.SZ`、`601872.SH`、`03616.HK` 为 ready/P1 正例。
  - `600519.SH` 为时效窗口 gap 控制。
  - `00171.HK`、`06161.HK` 为 related-person P2 控制。
- 性能边界：SFC 单 ticker 40 条正文扫描约 13-20 秒；三个 HK ticker 并行会因端点竞争升至约 47-50 秒，正式流程应顺序冻结或直接复用 overlay。branch runner 仍为约 2-3 秒。
- 测试：builder direct runner `20/20`，branch harness direct runner `31/31`；`py_compile`、`git diff --check` 通过。项目 venv 没有 pytest，遵守“不重新安装”边界。
- branch-vs-branch：40 个 raw-mode 项 + 7 个 synthetic，共 `37 ok / 2 review / 8 possible_regression`；8 行是 4 个 counterfactual 在 lite/medium 的重复。
- 明确发现但未在本轮修公式：
  - A/HK P1 注入后候选 `15_events` 从 5 升到 6/7。
  - SMCI P1 注入 AAPL 后仍为 68 分 `buy_candidate`。
  - 根因是评分函数读取标题词表而不读取结构化 `severity`，且缺少部分中英文官方处罚语义。
- 本轮效果评分：adapter+harness `9.0/10`；现有评分处理结构化 P1 `4.0/10`。公式保持冻结，下一步只设计 severity-aware 消费契约并复用同一冻结输入验证。

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

1. 冻结本轮 overlay 和 counterfactual 输入，不再扩大关键词或继续挑样本。
2. 设计最小 severity-aware 消费契约：官方结构化 `severity/entity_scope` 优先，P2 只 review，旧 raw data 继续走标题 fallback。
3. 先补纯函数测试和同输入 branch-vs-branch，再决定是否修改公式；目标是修复已证明的方向错误，不提高其他样本分数。
4. 增加真实 P0 issuer holdout 和 SFC issuer 级 P1/P0 正例；仍按固定时间窗口和官方列表顺序选样，避免事后挑选。
