# Scoring Validation 变更日志

> 当前文档记录 `codex/scoring-validation-guardrails` 分支上的评分验证、branch-vs-branch harness、证据冻结与文档治理改动。它是开发追溯文档，不是 agent 指令入口；影响 agent 行为的规则仍以 `AGENTS.md` 和相关 harness 文档为准。

## 2026-07-13

### `98b14c7` · upstream 集成正式合回评分分支并关闭零值 OCF 边界

- `codex/scoring-validation-guardrails` 已从 `120a6c9` 以 `--ff-only` 快进到隔离集成提交 `98b14c7`；原 merge commit `71be11f` 的双亲 ancestry 保持不变，没有重演冲突或 cherry-pick。
- 合回前的第一性原理审计发现并修复一个有效零值边界：最新 OCF 为 `0` 时不得过滤并错把旧期当最新期；顶层 canonical `ocf_to_net_income_ratio=0.0` 不得被嵌套旧值覆盖。未修改评分公式、权重或事件阈值。
- 新增 direct report / remote 控制流测试：`--no-open-report` 硬阻止浏览器；remote 显式安装 opt-in 正确透传；Ctrl+C 后 HTTP server 与 tunnel 均清理。基金 runner 另以 mock pipeline 验证二次确认、逐股失败不中断和汇总链接，没有触发真实 859 长循环。
- 正式分支验证：`py_compile`；flow/data-contract `15/15`；fund runner `7/7`；scoring consistency + branch harness + overlay builder + school scores `99/99`，总计 `121/121`；lite/medium 缓存篮子通过。
- 最终 merge gate：baseline=`120a6c9`，candidate=`98b14c7`，core + holdout + discovered cache + frozen overlays + synthetic adversarial 共 `60 raw + 7 synthetic = 67` 项，结果 `67 ok / 0 review / 0 possible_regression`。
- 所有 investment / overall / fundamental / panel 分数变化为 `0`，档位变化为 `0`。P0/P1 仍阻止不合理买入；P2、resolved、伪造、过期事件仍不误伤。
- 纯评分耗时本次观测为 `2.118s -> 1.932s`，候选约快 `8.8%`，`0` performance warning；该幅度按短进程噪声处理，只下结论“无性能回退”。
- 最终效果评分 `9.4/10`：上游修复已值得在正式评分分支吸收，且新增零值/清理对抗边界；剩余扣分仅是本轮安全边界内未运行真实网络 OCF/估值、真实基金 859 和真实 Cloudflare tunnel 端到端。
- 下一主线仍是官方事件解决态的 shadow overlay 关联，不继续调权重或扩标题关键词；建议模型 `GPT-5.6 Sol`，`高推理`。

### `71be11f` · 隔离吸收 upstream `fce996c` 并保持评分零漂移

- 从稳定检查点 `120a6c9` 创建 `codex/scoring-validation-upstream-fce996c`，以 merge 方式吸收 upstream `fce996c`，保留双亲 ancestry；未修改 `codex/scoring-validation-guardrails` 或 `codex/windows-local-stable`。
- `run.py` 冲突采用语义合并：保留 `--score-drift`、`--no-open-report` 和 Windows/Mac 路径行为，同时接入上游统一 direct-report 后处理、loopback HTTP、cloudflared 显式安装与隧道清理；修复 fund summary 设置 direct path 后仍被外层 `sys.exit(0)` 截断的问题。
- 对上游数据契约再收紧两处：
  - OCF 显式写入 `ocf` / `ocf_history` / `ocf_to_net_income_ratio`，不再回写 `fcf` 或 `financial_health.fcf_margin`。
  - 缺行业或行业映射失败时不制造 `industry_pe`；cninfo 跨行业均值只进入 `market_pe_reference` 披露字段，不参与 `pe_vs_industry`。
- 其他重叠文件按语义并集处理：保留 global-listing `G` 市场、成长 key alias、结构化事件评分和离线纯评分边界；接入 mutual fund legacy preflight、legacy registry shape、坏 `agent_analysis` fallback。
- 验证边界：未重装、未跑 deep、未运行 update；项目 venv 无 pytest，使用 `py_compile` 与 direct runner。
- 专项结果：v3.9.2 flow/data-contract `10/10`；scoring consistency `33/33`、branch harness `31/31`、overlay builder `26/26`、school scores `9/9`，合计附加 direct runner `99/99`；lite/medium 缓存篮子通过。
- 冻结输入对照：baseline=`120a6c9`，candidate=`71be11f` 的代码树；core + holdout + discovered cache + frozen overlays + synthetic adversarial，共 `60 raw + 7 synthetic = 67` 项，`67 ok / 0 review / 0 possible_regression`。
- 数量变化：investment / overall / fundamental / panel 最大绝对漂移均为 `0`，决策档位变化 `0`。HUBG P0 仍为 `59.9/watch`、事件维度 `2`；SMCI P1 仍为 `64.9/watch`、事件维度 `4`；伪造、已解决和过期 P1 仍保持事件维度 `5`。
- 性能：baseline `3.132s`，candidate `3.059s`，候选约快 `2.3%`，`0` performance warning。由于与正式评分分支完全同分，不需要再运行 `codex/windows-local-stable` 历史参考对照。
- 中立结论：上游 flow、OCF、registry、agent fallback 和 fund routing 修复值得吸收；原始 OCF/FCF 别名、跨行业 PE 冒充行业 PE、fund 外层早退不值得原样吸收，已在隔离分支收紧。建议后续合回正式评分分支，但本轮不直接合回。
- 公正评分：原始 `fce996c` 为 `7.8/10`（方向正确但有三处残余契约/控制流风险）；隔离集成结果为 `9.2/10`。扣分项是未在本轮做真实联网 OCF/估值抓取、真实 fund 859 路径和实际 Cloudflare tunnel 端到端测试。

### `418ae5b` · 结构化事件风险正式进入评分与三市场扩源

- 在 `score_fns.py` 增加最小 severity-aware 消费契约，不调整普通评分权重：
  - 仅官方域名、精确 issuer、有效时效和未解决的 P0/P1 可触发护栏。
  - P0：`15_events <= 2`、`investment_score <= 59.9`。
  - P1：`15_events <= 4`、`investment_score <= 64.9`。
  - P2、关联人、已解决事件只 review；非官方、模糊实体、未来/过期记录被拒绝。
  - 镜像按 canonical/source record 去重；结构化负面行不再触发正向新闻奖励。
  - 传统 `overall_score` 不变，交易护栏只影响 `investment_score`。
- 美股从 SEC 8-K 单层扩为三层：SEC submissions、litigation releases、trading suspensions。
- A 股新增证监会行政处罚决定，保留巨潮、上交所、深交所。
- 港股新增 HKEX issuer critical filings，保留 HKEX disciplinary actions、SFC enforcement。
- 新真实正例：
  - `HUBG`：SEC 8-K P0/P1。
  - `000851.SZ`：证监会处罚、巨潮重大违法退市风险、深交所处分。
  - `00841.HK`：HKEX issuer critical filing P1。
- 新对抗边界：伪造官方字段、已解决 P1、未来/过期 P1、非数字时效、镜像重复、P2/关联人不硬降级。
- 验证：branch harness `31/31`、builder `26/26`、scoring consistency `33/33`，`py_compile` 和 `git diff --check` 通过；未安装 pytest。
- 最终 branch-vs-branch：60 个 raw-mode 项 + 7 个 synthetic feature，共 `61 ok / 6 review / 0 possible_regression`；baseline/candidate 分别约 `2.7s/2.6s`。
- 关键变化：`HUBG P0 -> AAPL` 从 `68/buy_candidate` 收紧为 `59.9/watch`；`SMCI P1 -> AAPL` 收紧为 `64.9/watch`。伪造、已解决和超时效 P1 保持中性。
- 客观效果评分：结构化 P1 处理由 `4.0/10` 提升为 `8.8/10`；adapter+harness `9.3/10`；整体交付 `9.0/10`。扣分点是自动解决态追踪和部分官方列表的有界扫描，不为满分硬凑。
- 在线/离线边界冻结：在线只负责从官方源发现和冻结事实；离线负责实体匹配、日期、taxonomy、去重、评分和 branch 对照；Agent 只做发现、解释和冲突复核，不能凭经验创造 P0/P1。

### 三市场官方负面事件 adapters 与反事实对照（问题发现阶段）

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
- 当时效果评分：adapter+harness `9.0/10`；评分处理结构化 P1 `4.0/10`。该阶段只发现问题、未改评分；随后已由 `418ae5b` 的 severity-aware 消费契约和同输入复验闭环。

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

1. 评分权重和事件阈值继续冻结，先做一段时间的 production shadow 观察，不让在线证据直接改动评分代码。
2. 下一项高收益工作是“事件生命周期关联”：将后续整改、解除停牌、恢复合规等官方公告关联到 canonical event，生成可复核的 `resolution_status`，仍先进入 overlay 再对照。
3. 对 NYSE/Nasdaq 等动态列表只做 schema 稳定性评估；没有稳定官方字段时保持 gap，不以页面抓取数量换覆盖率。
4. 持续按固定窗口和官方列表顺序补自然出现的 P0/P1 holdout，不围绕当前阈值挑样本，也不继续扩张标题关键词。
