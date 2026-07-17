# UZI-Skill 交接记录 - 2026-07-08

## 2026-07-17 FX/FCFF shadow 停止线

- 当前隔离分支 `codex/scoring-validation-fx-fcff-shadow`，基线 `4afce20`，实现提交 `af59243`。通过硬门禁后应 fast-forward 合回并继续在正式 `codex/scoring-validation-guardrails` 开发；不要合到 `main`、`codex/windows-local-stable` 或历史实验分支。
- 真实 FX：Yahoo direct/inverse/triangle + 同日 ECB 官方交叉盘，CNY/HKD、CNY/USD、USD/HKD 全部通过，跨源误差 `0.054045%/0.019265%/0.018544%`。HKMA 最新值滞后 17 天，只作参考，不视为新鲜数据。
- 真实 FCFF：11 个 A/US/HK 样本 `0/11` 可进入生产。AMZN 两法一负一正且差 `162.7959%`；BABA/09988 差 `110.4038%`；即使 600519 只差 `0.0722%`，也缺发行人利息现金流分类证明。不要继续用字段名或数值接近推断 FCFF。
- 验证：`175/175` direct tests、`py_compile`、`git diff --check`；frozen branch compare `71 ok / 0 review / 0 possible_regression`，全部分数/档位零变化；六轮纯评分中位 `2.8s -> 2.5s`，仅判无回退。
- 保留审计工具/冻结证据/测试；不把 FX/FCFF 数值接生产，不新增静态 WACC/增长/税率 clamp，不修改金融机构估值。完整表见 `docs/fx-fcff-shadow-validation.md`。
- 下一步使用 `GPT-5.6 Sol` + `高推理`，但只在逐发行人闭环 FCFF 会计政策、金融机构模型或跨市场 WACC 契约时继续；普通维护无需为“继续开发”而扩大模型面。

## 2026-07-17 正式分支合回与资本桥/FCFF 语义收口

- 分支判断已经执行：`codex/scoring-validation-real-shadow-hardening` 先合到正式评分分支；本轮 `codex/scoring-validation-balance-sheet-fx-shadow` 通过全部门禁后又以 `--ff-only` 合回。当前分支与 origin 均为 `codex/scoring-validation-guardrails@0b74234`。不要合到 `main`、`codex/windows-local-stable` 或历史 `codex/scoring-validation-upstream-fce996c`。
- 隔离实现提交 `ac4e1ad`：CFO-capex/Yahoo FCF 标记为 `levered_cash_flow_proxy`；企业价值 DCF 仅接受真正 FCFF；美股同期间债务/现金桥带 provenance，缺失不补 0；现金流使用财报币种。
- 真实证据：A/US/HK 10 标的 Yahoo+新浪/东财交叉；AAPL FCF 两源 0 差异，腾讯债务/现金 `2.59%/0%`，阿里债务/现金/FCF `7.71%/0%/1.72%`。宁德时代供应商 FCFF/FCFE 与 CFO-capex 差 `80.76%/93.42%`，MSTR FCF 差 `99.50%`，因此不接入生产。完整表见 `docs/cross-market-capital-bridge-shadow.md`。
- 验证：核心/评分/harness/overlay `130/130`，基金/路由/学校 `27/27`，评分校准 `7/7`；`py_compile`、`git diff --check` 通过。branch compare `71 ok / 0 review / 0 possible_regression`，所有分数和档位变化为 0；纯评分三轮中位数 `2.400s -> 2.300s`，无性能回退。
- 遗留：SEC Companyfacts 当前网络 403；时间戳 FX、真正 FCFF、FCFE 专用折现、跨市场市场参数和金融机构估值尚未闭环。不要用静态 FX/WACC 或供应商字段名直接填坑。
- 已执行：隔离分支已 fast-forward 合回并推送正式评分分支。后续常规开发继续在 `codex/scoring-validation-guardrails`；新的 FX/FCFF 研究仍先从正式点另开隔离分支。下一步使用 `GPT-5.6 Sol` + `高推理`。

## 2026-07-15 A/US/HK 真实 shadow 与估值安全收口

- 隔离分支 `codex/scoring-validation-real-shadow-hardening`，实现提交 `a21e554`，基线 `1e9ccd9`。正式 `codex/scoring-validation-guardrails` 与 `codex/windows-local-stable` 均未修改；只能 push 个人 origin，upstream push 继续 `DISABLED`。
- 10 个真实标的年度 FCF shadow 已保存到 `local-ops/state/valuation-shadow/20260715-a-us-hk/`。低归一化风险只出现在 600519 和 AAPL 的 shadow 诊断，但二者仍分别缺生产净债务桥和非 A 市场折现率契约；不能据此启用生产 DCF。金融机构 601318/JPM/00005、负 FCF MSTR/09988、波动/符号翻转 300750/AMZN，以及 HK 跨币种均被明确 gate。
- 生产 DCF 移除全部利润/收入/市值代理，要求真实正 FCF、非金融机构、债务现金桥、可靠股数、币种一致和已验证市场 WACC；失败原因进入 report/self-review。结构化 P0/P1 同时校验 published/as-of/age，伪造或缺失时间信息不再触发硬决策。
- 真实 600519 基金 medium：993 源行、671 主动、20 full、651 lite、40 次预算上限、18.548 秒；无 859/993 无界循环。真实 AAPL 生产链复验得到 314.86 美元、46244.6081 亿美元市值、146.874 亿股且交叉校验通过；当次 financial endpoint 未返回可消费 FCF，且非 A WACC 未验证，因此安全拒绝 DCF。
- 验证为 `171/171` direct tests、`py_compile`、`git diff --check`、lite/medium 缓存篮子通过。正式 frozen report：`local-ops/state/branch-score-compare/20260715-real-shadow-hardening-final.md`，`71 ok / 0 review / 0 possible_regression`，分数与档位变化全为 0。三轮纯评分中位数 `3.985s -> 3.259s`，只判定无性能回退。
- 建议：将本隔离分支的 fail-closed、单位/币种和事件时间契约合回正式评分分支；暂不吸收多年 FCF 归一化、FCFF/FCFE 或跨市场 WACC 参数。下一阶段先补可审计 A/HK balance-sheet 与 FX 桥，再做只读 shadow。推荐 `GPT-5.6 Sol` + `高推理`。

## 2026-07-14 现金流量表 FCF 与 DCF 口径收口

- 正式分支 `codex/scoring-validation-guardrails`；代码检查点 `ea00a73`。只允许 push 个人 origin，upstream push 仍必须 `DISABLED`，`codex/windows-local-stable` 不修改。
- A 股现以同期 `NETCASH_OPERATE - CONSTRUCT_LONG_ASSET` 得到衍生 FCF；US 股使用 yfinance cashflow `Free Cash Flow`。负 FCF 不再回退利润代理，FCF 缺失时才保留明示标记的净利×0.8 fallback。
- 真实同日对比：600519 DCF `14528.0亿 -> 12882.0亿`（`-11.3%`）；688017 `21.9亿 -> 11.5亿`（`-47.5%`）；AAPL `19767.7亿 -> US$21788.2亿`（`+10.2%`）；MSTR 真实 FCF `-225.8亿 USD`，DCF 不适用。
- HTML 估值卡现可见披露 DCF 输入类型、期间、值、币种和模型警告；AAPL 不再错标为人民币，并对数据文本做 HTML 转义。
- 真实基金富化：600519 的 `993` 源行/`671` 主动列表在 hard cap=`2` 时仅 4 次调用，2 家 full + 669 家 lite，`2.2–2.9s`完成。
- 验证总计 `160/160` direct tests，`py_compile`、`git diff --check`、lite/medium 篮子通过。最终报告 `local-ops/state/branch-score-compare/20260714-real-fcf-final.md`：`71 ok / 0 review / 0 possible_regression`，分数和交易档位变化为 0。
- 三轮纯评分中位数 `2.660s -> 2.607s`，无性能回退；不宣称稳定提速。公正效果评分 `9.6/10`。
- 下一步只做 shadow 研究：用真实 A/US/HK 对比单年 FCF、多年归一化、FCFF/FCFE 与净债务桥接；在口径冲突解决前不改 DCF 假设、不调分。推荐 `GPT-5.6 Sol`，`高推理`。

## 2026-07-14 真实数据契约收口

- 正式分支仍为 `codex/scoring-validation-guardrails`；代码检查点 `952342d`。个人 origin 是唯一 push 目标；upstream push 必须继续 `DISABLED`，不操作原作者 PR，不修改 `codex/windows-local-stable`。
- 真实 `600519.SH` 暴露当前东财 OCF 字段 `NETCASH_OPERATE`；旧逻辑静默为空。修复后 2026Q1 OCF `269.1亿`，2025 年报 `615.22亿`，同年 OCF/净利 `0.75`；季度与年度不再混除，OCF 不再被当作 FCF。
- 真实 `688017.SH` 缺行业时保持 `industry_pe=—`，跨行业 `33.2` 只披露为 market reference；DCF 明示标记为净利×0.8 代理，不是财报 FCF/OCF。
- 真实 `600519.SH` 基金源为 `993` 行/`671` 主动/`322` 被动；lite 全列表保留，完整统计默认 hard cap `50`，无界扩展必须显式 opt-in。`510300.SH` 和 `110011` 真实识别/持仓路由通过；`run.py 110011` 以退出码 0 无 traceback 分流到 legacy。
- SMCI/HUBG/AAPL 官方 overlay 已刷新到 `2026-07-14`。没有新的精确终局证据，因此没有扩展生命周期规则：Item 4.01、4.02、HUBG 3.01 继续不解除风险，AAPL gap 不被推断为安全。
- 验证总计 `156/156` direct tests，`py_compile`、`git diff --check`、lite/medium 缓存篮子全通过；未重装、未跑 deep、未运行 update。
- 最终对照报告 `local-ops/state/branch-score-compare/20260714-live-data-contract-final.md`：`71 ok / 0 review / 0 possible_regression`，所有分数和交易档位变化为 0。三轮纯评分中位数 `2.186s -> 2.177s`，无性能回退。
- 建议合回/保留：当前就是正式评分分支，建议保留并推送本次修复；不需要对 `codex/windows-local-stable` 做历史参考对照。公正效果评分 `9.5/10`。
- 下一步不调分、不扩关键词。只有出现精确 issuer+精确 case/rule topic+官方终局语言时，才 shadow 扩展另一生命周期事件族。推荐 `GPT-5.6 Sol`，`高推理`。

## 2026-07-13 官方事件解决态闭环

- 实现检查点 `f8f235b`；真实 SEC 生命周期把 SMCI 2024 年 3 条 Nasdaq Rule `5250(c)(1)` 记录关联到 2025-02-26 官方 closed 记录，两个 Item 4.01 仍 active。
- 同 CIK/同主题/后续日期/canonical link 防伪、12 个冻结官方 overlay、`138/138` direct tests 和 `71/71` 分支对照均已完成；`0 possible_regression`，评分公式和阈值未改。
- 报告：`local-ops/state/branch-score-compare/20260713-real-event-lifecycle-final.md`。正式单次 `1.697s -> 1.807s`，三次中位数 `1.697s -> 1.696s`，均无性能告警。
- 真实决策边界：仅已关闭 3.01 注入 AAPL 为 `68/buy_candidate`、事件维度 5；未解决 4.01 注入 AAPL 为 `64.9/watch`、事件维度 4。
- 下一步不再修本轮代码；若扩展 A/HK 或其他 SEC 事件族，继续先 shadow 后消费。推荐 `GPT-5.6 Sol`、`高推理`。

## 2026-07-13 upstream fce996c 正式合回完成

- 正式分支：`codex/scoring-validation-guardrails`；代码检查点：`98b14c7`。它由稳定点 `120a6c9` 对隔离分支执行 `--ff-only` 得到，保留 `71be11f` 的 upstream 双亲 ancestry。
- 隔离分支 `codex/scoring-validation-upstream-fce996c` 已先推送到个人 origin；正式分支推送目标仅为个人 `origin/codex/scoring-validation-guardrails`。`codex/windows-local-stable` 未修改，upstream push 仍为 `DISABLED`，未创建原作者 PR。
- 合回前额外修复：合法最新 OCF `0` 不再被过滤成旧期；canonical 顶层 OCF/净利比 `0.0` 不再回退到嵌套旧值。评分公式、权重、结构化事件 P0/P1 阈值均未改。
- 正式分支专项：flow/data-contract `15/15`、fund runner `7/7`、既有 direct runner `99/99`，总计 `121/121`；`py_compile` 与 lite/medium 缓存篮子通过。
- 最终对照：`local-ops/state/branch-score-compare/20260713-upstream-fce996c-final-merge-gate.md`，`67 ok / 0 review / 0 possible_regression`；所有分数和档位变化为 0。
- 性能：`2.118s -> 1.932s`，本次约快 `8.8%`，无告警；只判定无回退，不把短时差异解释为确定优化收益。
- 公正评分：正式集成 `9.4/10`。确定性测试已覆盖 fund 二次确认/部分失败、report no-open、remote opt-in 和清理；真实网络 OCF/估值、真实 859 基金与真实 Cloudflare tunnel 仍是外部端到端残余风险。
- 下一项：只做官方 resolution/remediation/closed 的 shadow overlay 生命周期关联，再用同一冻结输入验证；不扩关键词、不改权重。建议 `GPT-5.6 Sol`，`高推理`。

## 2026-07-13 upstream fce996c 隔离集成

- 隔离分支：`codex/scoring-validation-upstream-fce996c`；merge commit：`71be11f1ebb6058faf03429b1208dfc0b11388a0`，双亲为稳定检查点 `120a6c9` 与 upstream `fce996c`。
- 个人 `main` 已 fast-forward 到 `fce996c` 并只推送 `origin/main`；`upstream.pushurl=DISABLED` 保持不变。未修改 `codex/scoring-validation-guardrails`、`codex/windows-local-stable`，未操作原作者 PR。
- `run.py` 冲突保留 score drift / no-open 语义并接入统一 direct-report / remote 后处理；额外修复 fund summary 被外层 early exit 截断。
- OCF 与 FCF 已隔离；缺行业时不再把跨行业 PE 写成 `industry_pe`。registry、mutual-fund legacy routing、坏 agent payload fallback 均通过专项测试。
- 验证：`py_compile`；flow/data-contract `10/10`；其余 direct runner `99/99`；lite/medium 缓存篮子通过。
- branch-vs-branch 报告：`local-ops/state/branch-score-compare/20260713-upstream-fce996c-integration.md`。`60 raw + 7 synthetic`，结果 `67 ok / 0 review / 0 possible_regression`；所有评分漂移与档位变化均为 0。
- 性能：baseline `3.132s`，candidate `3.059s`，约快 `2.3%`，无告警。无需再跑 windows-local-stable 历史对照。
- 建议：可以把该隔离分支合回正式评分分支，但必须保持单独 review，不在本轮直接合回。剩余风险仅是受本轮边界限制而未做真实网络 OCF/估值、fund 859 和 Cloudflare tunnel 端到端。
- 下一步模型：`GPT-5.6 Sol`，`高推理`；任务应限定为复核 `71be11f` 后把隔离分支合回 `codex/scoring-validation-guardrails`，不再改评分公式。

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
