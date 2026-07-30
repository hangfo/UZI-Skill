# UZI-Skill 交接记录 - 2026-07-08

## 2026-07-30 SEC/FRED/Massive 安全 shadow 与真实动量复核

- 当前隔离分支 `codex/scoring-validation-sec-fred-massive-shadow`，起点
  `3b8637a`，已验证代码提交 `5873eac`；正式 `codex/scoring-validation-guardrails` 及 origin 均为
  `fff93f6`，upstream/main=`fce996c`，upstream push=`DISABLED`。
- 新增 DPAPI 遮罩配置、FRED evidence-only shadow、Massive EOD non-mutating
  对照；TradingView Premium 不作为行情 API，CBOE 零联网。
- PATH/IREN/HURN/GRMN/MANH/AVTR 真实生产均 critical=0；综合
  `48.4/45.7/45.1/52.3/45.8/40.4`。六股 724 信号回测的技术分-超额相关
  `-0.021/-0.036/-0.000`，不调动量或 Stage。
- SEC/FRED/Massive 脱敏真实端点通过；FRED 8/8 ready，Massive 六股均真实落后
  Yahoo 一日且不覆盖主序列。IREN 4.01 正文无审计分歧，引用的内控缺陷已整改，
  保持 ambiguous，不进入评分。
- 正反 `103/103 ok`、0 review、0 possible regression、评分/档位零变化；
  direct `230/230`，py_compile/diff/JSONL 通过。可以提交并只推送隔离分支；
  不要自动合回正式分支。完整报告：
  `docs/sec-fred-massive-secure-shadow-validation-20260730.md`。

## 2026-07-29 US entity 正式吸收门禁与热门股压力验证

- 隔离分支代码提交 `3b8840b` 相对正式 `48e20fc4c9fe9823ab055155511be3bc503cb78b` 为纯 fast-forward；upstream/main 保持 `fce996c`，upstream push 为 `DISABLED`，`main` 和 `codex/windows-local-stable` 未修改。
- AAL 真实生产事件从 9 条净化到 6 条：United/Delta 合并传闻和泛航空股标题不再由 `American/airline(s)` 通用拆词拥有；完整 `American Airlines` 与 `AAL Stock` 仍召回。窄审计观察 precision `66.7% -> 100%`、recall `100% -> 100%`。
- 三批 349 条 Yahoo 冻结集保持 `TP=166/FP=0/FN=1`、precision `100%`、recall `99.40%`、污染和重复率均 `0`。唯一 FN 无发行人实体证据，继续 fail-closed。
- 最新真实生产：AAL lite `43.7/46.8/Stage 2/回避`，PLUG lite `39.5/34.2/Stage 1/回避`，INCY medium `54.2/75.2/Stage 2/关注但综合观望偏空`，PLTR medium `49.3/56.0/Stage 4/谨慎观察`。
- 8 股历史压力集 1103 个真实信号表现较强，但有当前热门股选择与幸存者偏差；不覆盖 37 股主回测，不调评分、动量、Stage、事件阈值或估值参数。
- 正式对候选加四股缓存为 `99/99 ok`、0 review、0 possible_regression，评分/档位零变化；正向 `3.529s -> 3.948s`，交换顺序 `4.572s -> 3.352s`，无性能告警。direct `128/128`。
- 完整文档：`docs/us-entity-formal-integration-momentum-stress-20260729.md`。下一步 `GPT-5.6 Sol + 高推理` 只做按历史时点冻结且包含退市股的无幸存者偏差 US 宇宙；数据条件不满足则停止动量优化，改为持续监控真实 entity FP/FN。

## 2026-07-29 entity 合并审计与真实收益回测

- 当前分支仍为 `codex/scoring-validation-us-entity-recall-shadow`；正式分支/个人 origin 保持 `48e20fc4c9fe9823ab055155511be3bc503cb78b`，本分支起点为 `a48f4b3b74f07a41ba1ef3b6b32b516602150a39`。不要自动合回正式分支。
- 三批真实 Yahoo 集共 349 行复核：候选行级合计 `TP=166/FP=0/FN=1`，precision `100%`、recall `99.40%`、污染 `0`。唯一 FN 是无发行人主语的泛 Big Tech 日程标题，继续 fail-closed。
- 新增只读 `tools/us_momentum_walkforward.py`：37 只美股、SPY、10 年复权日线、4518 个不重叠 21/63/126 日真实信号、20bp 摩擦。完整技术分数没有单调收益证据；Stage 2 相对 Stage 4 在全样本较强但早期分段不稳定。结论是不调分、不新增动量规则。
- 最新生产 LCID lite `41.1`（投资分 31.2、Stage 4、回避）与 CLS medium `51.4`（投资分 65.7、Stage 2，但综合观望偏空），均 `critical=0`。
- 冻结对照扩展到 `93/93 ok`、`0 review`、`0 possible_regression`，全部评分/档位零变化；正向 `7.915s -> 7.268s`、交换顺序 `5.073s -> 6.682s`，均无 performance warning。direct `113/113`。
- 完整文档：`docs/us-entity-merge-audit-momentum-backtest-20260729.md`。SEC 因无真实联系人未请求，CBOE 零请求；未装依赖、未跑 deep/update。下一步默认 `GPT-5.6 Terra + 中推理` 做正式 fast-forward 文件审计；真实冲突或全市场无幸存者偏差研究才用 `GPT-5.6 Sol + 高推理`。

## 2026-07-29 第三批 US entity holdout 与短 ticker 污染修复

- 当前隔离分支 `codex/scoring-validation-us-entity-recall-shadow`，正式基线仍为 `48e20fc4c9fe9823ab055155511be3bc503cb78b`，候选代码检查点 `91cb6eb22f8cac4970617c8036c5b3bc022426df`。`main`、`codex/windows-local-stable`、正式分支均未修改；upstream push 仍为 `DISABLED`。
- 150 条真实 Yahoo 标题：修改前 precision/recall/污染率 `86.67%/100%/12.82%`，修改后 `100%/100%/0`。10 个 FP 是 4 条 Nu Skin→NU 和 6 条 T. Rowe Price→T；0 FN。官方 IR 只绑定 `Nu Holdings/Nubank/AT&T`，没有放宽 substring。
- 真实生产 NU medium `51.6`、MARA medium `42.5`、T lite `47.6`、FOUR lite `44.1`，均 `critical=0`。生产事件净化移除 Shift4 前 CEO/SpaceX 1 条和 D-Wave 主体/AT&T 对手方 2 条，评分与档位不变。
- 验证：`113/113` direct tests；`79/79 ok`、0 review、0 possible_regression；全部评分/档位零变化；正反顺序无 performance warning。SEC 无真实联系人未请求，CBOE 未联网。
- 建议值得吸收但不要自动合回。下一步用 `GPT-5.6 Terra + 中推理` 做独立标签/合并审计；只有正式分支冲突或新真实实体消费冲突时才用 `GPT-5.6 Sol + 高推理`。完整报告：`docs/us-entity-recall-third-holdout-validation-20260729.md`。

## 2026-07-29 美股实体召回独立复采与热门股门禁

- 当前隔离分支 `codex/scoring-validation-us-entity-recall-shadow`，正式基线仍为 `48e20fc4c9fe9823ab055155511be3bc503cb78b`，候选代码检查点 `1a3b60b`。`main`、`codex/windows-local-stable`、正式评分分支均未修改；upstream push 保持 `DISABLED`。
- 新增独立 80 条真实 Yahoo 集 `MSTR/KNSA/OSCR/IQV/LCID/NVDA/ITRI/MU`。修改前 precision/recall/污染率 `97.73%/97.73%/2.27%`，修改后 `100%/100%/0`；旧 119 条集继续 `100%/98.28%/0`。
- 修复仅包括官方可证的 `MicroStrategy→Strategy` 更名与明确 partner/supplier/customer 反向污染。`Strategy` 是 stopword，只接受发行人事件模板；不加入 Saylor 等人物名，不放宽 substring。
- 真实生产 KNSA medium `66.9/观察`、OSCR lite `46.2/回避`、ITRI lite `59.0/谨慎观察`、MSTR medium `36.3/回避`，报告均生成、`critical=0`。IOND 只有 1 个历史观察，未被误称为动量股。
- direct runner `110/110`；冻结 `77/77 ok`、`0 review`、`0 possible_regression`，评分/档位零变化；正反顺序均无性能告警。SEC 无真实联系人未请求，CBOE 未联网。
- 完整报告：`docs/us-entity-recall-hot-followup-validation-20260729.md`。建议推送隔离分支但不自动合回；下一步用 `GPT-5.6 Terra + 中推理` 做独立标签复核和合回前审计，若发生代码冲突再用 `GPT-5.6 Sol + 高推理`。

## 2026-07-29 美股实体 alias 真实召回 shadow

- 当前隔离分支为 `codex/scoring-validation-us-entity-recall-shadow`，起点是正式检查点 `48e20fc4c9fe9823ab055155511be3bc503cb78b`。正式 `codex/scoring-validation-guardrails`、`main`、`codex/windows-local-stable` 均未修改；`upstream/main=fce996c`，upstream push 仍为 `DISABLED`。
- 119 条实时 Yahoo 冻结新闻覆盖 `MU/AI/C/F/GOOGL/META/HOOD/ON/IT/CAT/XYZ/GEN`。基线 precision/recall/污染率为 `89.47%/87.93%/10.53%`，候选为 `100%/98.28%/0`；基线 6 FP 和 7 FN 收敛为 0 FP、1 FN。
- alias 只接受发行人官方 investor-relations 的明确绑定；common-word ticker 必须有证券上下文。Citi、Google、Meta Family of Apps、onsemi、Cash App、Norton/Avast/LifeLock、MoneyLion 均保留来源和 binding。没有 SEC 真实联系信息，SEC 未请求；CBOE 未联网。
- 真实 AI lite、GEN medium 和 MU event fetch 通过；BigBear.ai、普通介词 on、Gartner 供应商稿与 Musk 不再污染。direct runner `108/108`，冻结 `79/79 ok`，`0 possible_regression`，分数/档位零变化，交换顺序性能无告警。
- 完整报告：`docs/us-entity-recall-shadow-validation-20260729.md`。冻结数据在 `local-ops/state/us-entity-recall-shadow/`，分支对照在 `local-ops/state/branch-score-compare/20260729-us-entity-recall-shadow-*.md`。
- 建议：值得吸收，但本轮不自动合回正式分支。下一轮先用 `GPT-5.6 Terra + 中推理` 在独立时点复采 Yahoo 并盲审标注；只有出现新的发行人关系/事件消费链重叠才升级到 `GPT-5.6 Sol + 高推理`。

## 2026-07-28 美股动量真实刷新与证据契约

- 隔离分支 `codex/us-momentum-real-refresh-20260728` 从正式 `e7241dc` 开始，代码检查点 `1f5251c`。修复 US/G 宏观缺失伪中性、pipeline 字符串 ticker 的 CN 误路由、短 ticker 新闻 substring 误匹配和普通 Apple/Tesla 比较触发供应链误报；没有改评分/阈值/估值/基金路由。
- 真实生产重跑 AAPL lite、AMD/MU medium；报告均生成，`critical=0`。MU 当前 Yahoo 新闻从误入 Musk/Tesla 改为 5 条 Micron/MU 相关记录；宏观搜索无证据时输出 `market=U/rate_market=US/null/fallback=true`。
- 真实热股矩阵还覆盖 HOOD、BMNR、SNDK、SPCX。AAPL/AMD/MU 分别 `50.2/48.0/52.6`；BMNR 单段反弹仍回避，HOOD Stage 4，SPCX 30 日历史仍不输出 MA200/年度精度。
- 与 07-20 对比 MU `52.8→52.6`、SNDK `47.6→47.6`、SPCX `38.3→38.3`，无档位变化。冻结 `75/75 ok`、`0 possible_regression`、全部分数/档位零变化；7 股 37 历史窗口零回退，31 轮纯计算中位 `0.073388s→0.073262s`。
- 详细复跑、客观评分、停止线和文件路径见 `docs/us-momentum-real-refresh-validation-20260728.md`。门禁完成后隔离分支只推个人 origin，并 fast-forward 到正式评分分支；后续继续在 `codex/scoring-validation-guardrails`。
- 下一项只 shadow 建立真实 US 公司 alias/官方事件漏召回率；没有真实增益前不放宽 entity match、不接静态宏观默认、不调动量权重。使用 `GPT-5.6 Sol + 高推理`；纯非重叠 release 审计才降为 `GPT-5.6 Terra + 中推理`。

## 2026-07-28 三方 release/HEAD 审计

- 从正式 `codex/scoring-validation-guardrails@6b295bd` 建立隔离分支 `codex/upstream-intake-20260728`。`upstream/main=fce996c` 已在 ancestry 内，当前 `ahead 62 / behind 0`；没有再 merge UZI，没有动 `main`、`codex/windows-local-stable` 或 upstream push/PR。
- 用户级 `a-stock-data` 已从官方 `v3.4.0` 更新为 `v3.5.1+uzi.1`；`global-stock-data` 从官方 `v1.0.1` 精确更新为 `v2.0.3`。前者本地补丁只修复东财当前实得 100-row page 导致 `top_n>200` 提前截断的问题，补丁基版、哈希和删除条件均已落盘。
- 真实交叉验证发现 UZI 自己的 `920xxx` transport 路由漂移：canonical market 是 BJ，但腾讯/新浪直连曾拼成 SH/SZ。候选实现统一复用 canonical prefix；真实 `bj920002` 在 data source、Tencent provider 和 Sina provider 三路均成功。
- 美股/港股现有 UZI 公共 Tencent quote 解析用 AAPL/00700 实测正常，不做无收益重写。板块资金流、FINRA short volume、SEC Frames、Treasury、CFTC、Nasdaq 和 CBOE 均不复制进默认生产链；其中 CBOE 未获授权不联网。
- 重跑入口：`D:\UZI-Skill\.venv\Scripts\python.exe tools\stock_skill_release_smoke.py --json-out local-ops\state\upstream-audit\20260728-stock-skills-real-smoke.json`。若 Eastmoney 临时不可达，可用 `--skip-board-flow` 完成其余独立端点，但必须把该项记录为 access gap。
- Eastmoney 随后已恢复并通过完整分页：`total=496 / returned=205`。冻结评分对照 baseline=`6b295bd`、candidate=`5cb1323` 为 `71/71 ok、0 possible_regression`，所有评分和交易档位零变化；三轮交换顺序整批中位数 `2.6s -> 2.3s`，无性能回退。direct runner `269/269`。
- 详细矩阵、剩余风险和长期策略见 `docs/upstream-intake-audit-20260728.md` 与 `docs/upstream-intake-policy.md`。全部冻结评分/性能门禁通过后才允许 fast-forward 正式分支；继续使用 `GPT-5.6 Sol + 高推理` 处理重叠代码，纯 release 审计可用 `GPT-5.6 Terra + 中推理`。
- 隔离分支已推送个人 origin，并已 `--ff-only` 合回正式 `codex/scoring-validation-guardrails`。下一步继续在正式评分分支；不要回到隔离分支继续堆叠常规开发。

## 2026-07-20 美股动量短历史契约

- 正式基线 `2fdc8b4`，隔离分支 `codex/scoring-validation-us-momentum-history`。修复只涉及技术历史完整性：Stage 至少 200 个真实观察，年度窗口至少 250 个；各 MA 不足自身周期时为 null。评分、事件、估值、基金和路由均未改。
- 真实 Yahoo 日线 9 股、49 个窗口结果为 `42 beneficial / 7 unchanged / 0 possible_regression`；成熟 MU/WDC/STX/SNDK/GEV/BMNR/CRCL full Stage 不变，FIG 242 日保留 Stage 4，SPCX 24 日保持 unknown 且不再输出伪 MA200/年度偏离。
- 真实生产重抓 MU lite、SNDK medium、SPCX lite，最新 K 线均为 `2026-07-17`；得分 `52.8/47.6/38.3`，报告已生成。网络补充维度缺口显式保留，没有默认填充。
- 冻结分支对照 `71/71`、`0 possible_regression`、评分和档位零变化；direct tests `213/213`。31 轮纯计算中位 `0.092015s -> 0.087824s`，无性能回退。
- 全部硬边界通过后，隔离分支已推送个人 origin，并已 fast-forward 合回正式 `codex/scoring-validation-guardrails`。后续继续在该正式评分分支开发；`main`、`codex/windows-local-stable` 和 upstream 未动。详见 `docs/us-momentum-history-validation.md`。

## 2026-07-17 三方上游择优吸收

- 当前开发分支仍为 `codex/scoring-validation-guardrails`；UZI 相对 `upstream/main=fce996c` 为 `ahead 55 / behind 0`，不需要再次合并。`upstream` push URL 保持 `DISABLED`，`main` 与 `codex/windows-local-stable` 未修改。
- 用户级 `a-stock-data` 已从无本地改动的 `v3.3.0` 更新到官方 `v3.4.0`；`global-stock-data v1.0.1` 已精确匹配上游，无需更新。
- v3.4.0 的 47 个 Python 块全部编译；CLS 实时电报、交易所龙虎榜、新浪资金流、深交所公告、解禁字段和行业排序均用真实网络数据通过。没有用 mock，也没有把这些示例重复移植进 UZI。
- `local-ops/windows/update-uzi.ps1` 现在默认只审计。它不再 reset 分支、安装依赖或自动合并；显式 `-Mode ApplySkills` 也只更新两个补充技能，并从不可变 release tag 下载、先备份再替换。
- 长期规则见 `docs/upstream-intake-policy.md`：补充技能走 release/hash/真实 smoke；UZI 走隔离 merge、同输入 lite/medium、事件护栏和性能门禁；重复 provider、营销变化和无真实缺口支撑的参数不吸收。
- 下一步常规开发继续在 `codex/scoring-validation-guardrails`。仅当新 UZI upstream 与评分/估值/路由重叠，或真实失败率证明需要把技能备源产品化时，使用 `GPT-5.6 Sol` + `高推理`；纯 release 审计用 `GPT-5.6 Terra` + `中推理` 即可。

## 2026-07-17 FX/FCFF shadow 停止线

- 隔离分支 `codex/scoring-validation-fx-fcff-shadow` 从基线 `4afce20` 完成，实现提交 `af59243`、文档检查点 `c3a226f`；已推送个人 origin，并已 fast-forward 合回正式 `codex/scoring-validation-guardrails`。当前及后续开发分支是正式评分分支；不要合到 `main`、`codex/windows-local-stable` 或历史实验分支。
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

## 2026-07-29 SEC / Yahoo 新鲜度后续交接

- 隔离分支：`codex/scoring-validation-sec-access-hardening`
- 起点：`codex/scoring-validation-guardrails@fff93f6388ed605c7cf56ad4cad7133eb7681018`
- SEC：默认离线；联网必须显式 `--allow-network`，并从用户级环境变量
  `UZI_SEC_USER_AGENT` 读取真实姓名/邮箱。当前未配置，真实 SEC 请求为 0。
- CBOE：无许可，保持 0 请求、0 路由；不要只设一个 ack 变量绕过许可流程。
- Yahoo：INTC/SOFI 的 yfinance 尾部曾落后一日；候选保留复权历史，只用 v8
  5 日尾部追加严格更新日期，同日不覆盖。
- 真实生产：INTC/SOFI/JBLU/AMKR/GLW/ONDS；GLW/ONDS 是修改后从无缓存完整入口，
  全部 `critical=0`。
- 冻结对照：`98 raw + 7 synthetic = 105`，正反顺序均
  `105 ok / 0 review / 0 possible_regression`，同输入评分/档位零变化。
- 回测：8 股、10 年、1045 信号；技术分 alpha 仍弱，禁止据此调动量/Stage/
  P0/P1/估值参数。
- 详细文档：`docs/sec-access-hardening-real-us-validation-20260729.md`
- 下一步：用户配置真实 SEC 身份后，用 GPT-5.6 Sol high 做少量官方 filing/event
  生命周期 shadow；没有身份则用 GPT-5.6 Terra medium 只积累自然 holdout。

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
