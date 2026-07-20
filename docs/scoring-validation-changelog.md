# Scoring Validation 变更日志

> 当前文档记录 `codex/scoring-validation-guardrails` 分支上的评分验证、branch-vs-branch harness、证据冻结与文档治理改动。它是开发追溯文档，不是 agent 指令入口；影响 agent 行为的规则仍以 `AGENTS.md` 和相关 harness 文档为准。

## 2026-07-20

### 美股动量短历史 fail-closed

- 从正式检查点 `2fdc8b4` 建立隔离分支 `codex/scoring-validation-us-momentum-history`。真实 Yahoo 日线发现旧版在只有 60-199 个交易日时用部分均值冒充 MA200 并判 Stage 1-4，不足 250 日还把年度高点偏离写成 `0`。
- 生产契约改为按真实观察数开放 MA5/10/20/60/120/200；Stage 至少需要 200 日，年度高低点和偏离至少需要 250 日。新增观察数/完整性字段及实际可观察区间高低点；不改评分、阈值、估值或路由。
- MU/WDC/STX/SNDK/GEV/BMNR/CRCL/FIG/SPCX 共 49 个真实历史窗口：`42 beneficial_contract_fix / 7 no_change / 0 possible_regression`。成熟 full Stage 全部不变，FIG 242 日保留 Stage 4 但不伪造年度精度，SPCX 24 日明确 unknown/null。
- 生产重抓：MU lite `52.8`、SNDK medium `47.6`、SPCX lite `38.3`，最新日线均为 `2026-07-17`；无 traceback。冻结评分对照 `64 raw + 7 synthetic = 71`，`71 ok / 0 review / 0 possible_regression`，所有评分/档位变化为 0。
- 31 轮纯计算中位数 `0.092015s -> 0.087824s`，无性能回退；direct tests `213/213`、`py_compile`、`git diff --check` 通过。完整结论见 `docs/us-momentum-history-validation.md`。
- 全部门槛通过后，隔离分支已推送个人 origin，并以 fast-forward 合回正式 `codex/scoring-validation-guardrails`；后续开发继续使用正式评分分支。

## 2026-07-17

### 三方上游审计与补充数据技能 v3.4.0

- 实时核对 `a-stock-data`、`global-stock-data` 和 `wbh604/UZI-Skill`：仅 `a-stock-data` 从本地 `v3.3.0` 落后到 `v3.4.0`；`global-stock-data v1.0.1` 与上游内容一致；正式评分分支已包含 `upstream/main=fce996c`，为 `ahead 55 / behind 0`。
- 本地 `a-stock-data` 与官方 `v3.3.0` blob 哈希一致，无私人改动，已精确升级到不可变 release `v3.4.0`。没有把同类示例函数复制到 UZI 生产流水线，也没有修改评分、估值、路由或缓存契约。
- 真实验证而非 mock：47 个 Python fenced blocks 全部可编译；财联社签名电报返回实时记录；交易所龙虎榜、600519 新浪资金流、000001 深交所公告均返回真实数据；002475 解禁的 type/shares/able_shares 均非空；100 个行业按涨跌幅正确排序。
- Windows 更新入口改为默认只审计；移除自动硬重置、自动合并、自动安装依赖和滚动 main 覆盖。技能更新必须显式使用 `-Mode ApplySkills`，且只从 release tag 下载并先备份。UZI 代码永远走隔离分支与同输入回归门禁。
- UZI 重叠审查结论：解禁、行业、CLS、龙虎榜、资金流和公告在 UZI 已有消费链或多源 fallback；未证明真实覆盖缺口前不重复接入，避免口径混用、重复事件计权与性能回退。完整规范见 `docs/upstream-intake-policy.md`。

### `af59243` · 时间戳 FX 官方交叉验证与 FCFF 重建停止线

- 从正式检查点 `4afce20` 建立隔离分支 `codex/scoring-validation-fx-fcff-shadow`；没有修改生产评分、DCF、WACC、增长率、基金路由、`main`、`codex/windows-local-stable` 或 upstream。
- 三组真实 FX 合约同时校验 Yahoo direct/inverse/triangle 与同日 ECB 官方交叉盘；CNY/HKD、CNY/USD、USD/HKD 的跨源误差分别为 `0.054045%/0.019265%/0.018544%`，三组均通过 shadow 门槛。HKMA 最新记录滞后 17 天，显式降为 reference-only，不用权威性掩盖时效缺口。
- 11 个 A/US/HK 真实年度报表样本比较 partial EBIT bridge 与 FCF+after-tax-interest。600519/300750/腾讯虽只差 `0.0722%/4.0811%/4.3977%`，但利息现金流分类仍未验证；AMZN 差 `162.7959%`，BABA/09988 差 `110.4038%` 且方向冲突。FCFF 因此 `0/11` 晋级，金融机构继续不适用。
- `175/175` direct tests、`py_compile`、`git diff --check` 通过；未安装 pytest、未重装、未跑 deep、未运行 update。冻结对照 baseline=`4afce20`、candidate=`af59243`：`71 ok / 0 review / 0 possible_regression`，全部分数与档位变化为 0。
- 六轮交换顺序纯评分中位数 `2.8s -> 2.5s`，只判定无性能回退。建议吸收只读审计工具/证据/测试；放弃本轮 FCFF 产品化，不新增静态 FX/WACC 或自动换汇。完整结论见 `docs/fx-fcff-shadow-validation.md`。
- 全部硬门禁通过后，隔离分支已 fast-forward 合回正式 `codex/scoring-validation-guardrails` 并推送个人 origin；隔离分支也已留存在个人 origin 供审计。后续开发继续在正式评分分支，不合到 `main` 或历史 Windows 基线。
- 公正效果评分 `9.5/10`：高收益来自证明 FX 桥可审计、同时用真实反例阻止错误 FCFF 进入生产；扣分来自发行人会计政策、SEC Companyfacts、金融机构估值和跨市场 WACC 尚未闭环。

### `ac4e1ad` · 现金流类别、同期间资本桥与 A/US/HK 真实交叉验证

- 已验证的 `codex/scoring-validation-real-shadow-hardening` 先以 fast-forward 合回正式 `codex/scoring-validation-guardrails`，正式分支从 `1e9ccd9` 前进到 `3af25a3` 并推送个人 origin；`main`、`codex/windows-local-stable`、upstream 均未修改。后续开发在隔离分支 `codex/scoring-validation-balance-sheet-fx-shadow` 完成。
- 第一性原理修正：`CFO-capex` 与 Yahoo FCF 明确标为 `levered_cash_flow_proxy`，不能作为 FCFF 折现为企业价值后再扣净债务。现有企业价值 DCF 仅接受明确 `fcff`，否则 fail-closed。
- 美股资产负债桥只接受同一期报表值，记录期间、财报币种、basis 和来源字段；缺债务/现金不再静默写 0。现金流币种改用 `financialCurrency`，真实 BABA 从错误风险收口为财报 CNY/报价 USD 的显式错配。
- 新增真实 10 标的跨源 capital-bridge shadow。600519/300750 的债务和严格现金两源均零差异；AAPL FCF/现金零差异，腾讯债务/现金差 `2.59%/0%`，阿里债务/现金/FCF 差 `7.71%/0%/1.72%`。宁德时代供应商 FCFF/FCFE 与 CFO-capex 差 `80.76%/93.42%`，MSTR FCF 差 `99.50%`，证明这些字段不可混用。
- SEC Companyfacts 在当前网络返回 403，已显式保留为遗留项；没有以估算或 mock 补齐。FX、静态 WACC、FCFE 路径和金融机构专用估值继续暂缓，避免过拟合和伪精确。
- 验证：`py_compile`、`git diff --check`；核心专项 `130/130`、基金/路由/学校 `27/27`、评分校准 `7/7`。修复了“不同轴向必须产生不同整数总分”的脆弱测试，但没有调整评分公式。
- 中立对照 baseline=`3af25a3`、candidate=`ac4e1ad`：`71 ok / 0 review / 0 possible_regression`，全部评分和档位变化为 0。三轮纯评分中位数 `2.400s -> 2.300s`，只判定无性能回退。
- 全部硬门禁通过后，隔离分支以 fast-forward 合回正式 `codex/scoring-validation-guardrails`，正式实现/文档检查点为 `0b74234` 并已推送个人 origin；后续常规维护继续在正式评分分支，新的实验仍从该点另开隔离分支。
- 公正效果评分 `9.6/10`：阻断了杠杆后现金流重复扣债、缺失债务/现金伪装为零和跨币种错标，同时评分零漂移。扣分来自 SEC 官方源暂不可达、FX/FCFF/金融机构模型尚未闭环。

## 2026-07-15

### `a21e554` · A/US/HK 真实估值 shadow 与 DCF fail-closed 契约

- 从稳定检查点 `1e9ccd9` 建立隔离分支 `codex/scoring-validation-real-shadow-hardening`；没有改写正式评分分支、`codex/windows-local-stable` 或 upstream。三名只读裁判分别复核估值语义、跨市场真实数据和对抗边界。
- 真实 shadow 共 10 个标的：A 股 `600519/300750/601318`，US `AAPL/AMZN/MSTR/JPM`，HK `00700/09988/00005`。保存财报年度 FCF、最新值、3Y/5Y 中位数、MAD、符号翻转、财报/报价币种和生产硬门槛；不把 shadow 多年归一化直接写入生产模型。
- 最新/3Y 中位数（亿）：600519 `583.95/639.73`、300750 `908.75/658.10`、601318 `6502.77/3757.96`；AAPL `987.67/995.84`、AMZN `76.95/322.17`、MSTR `-225.80/-221.39`、JPM `-1477.82/-420.12`；腾讯 `1901.71/1745.55`、阿里 `-507.24/775.37`、汇丰 `251.05/354.16`。
- 生产 DCF 现必须同时满足：明确非代理 FCF、正 FCF、非金融机构、债务/现金股权桥、有效股数及市值交叉校验、现金流/报价同币种；非 A 市场还必须显式提供已验证市场折现率契约。任一缺失即返回可审计原因，不再用净利×0.8、收入×利润率或市值×5%制造估值。十个真实样本当前均至少触发一项生产 gate，因此 `0/10` 直接生成内在价值，这是安全拒绝而非评分降级。
- US 旧缓存裸数市值统一换算为亿元，显式 `market_cap_yi` 与“亿”字符串保持原口径；股数优先取 provider 明确字段，衍生股数必须通过市值/价格 10% 交叉校验。报告显示 fail-closed 原因；`terminal growth >= WACC` 直接拒绝。
- 结构化 P0/P1 事件增加 published/as-of/age 三者一致性校验，缺日期、自报 age、伪造 age、未来或过期记录不能进入硬门槛；P2、resolved 和 counterfactual 非伤害边界保持不变。真实基金 medium 补验为 `993` 源行、`671` 主动、`20` full、`651` lite，预算上限 `40` 次网络调用、`18.548s`，没有恢复 859/993 无界循环。
- 验证：项目 venv 无 pytest且未安装依赖；新增 stdlib direct runner，专项/评分/harness/overlay/US/fund/school/registry 合计 `171/171`。`py_compile`、`git diff --check`、真实 lite/medium 缓存篮子通过；未重装、未跑 deep、未运行 update。
- 冻结分支对照 baseline=`1e9ccd9`、candidate=`a21e554`：`64 raw + 7 synthetic = 71` 个 lite/medium 配对结论，`71 ok / 0 review / 0 possible_regression`；所有分数变化与交易档位变化均为 `0`。三轮交换顺序纯评分耗时：基线 `5.546/3.007/3.985s`（中位 `3.985s`），候选 `3.658/3.005/3.259s`（中位 `3.259s`），无性能告警；只判定无回退。
- 公正效果评分 `9.4/10`：收益来自阻断伪精确估值、补齐跨市场单位/币种/金融机构边界，同时纯评分零漂移。扣分项是生产链尚未具备完整 FCFF/FCFE 分类、A 股债务/现金桥、HK FX 桥和 US/HK 市场 WACC 参数，因此建议吸收 fail-closed 修复，但不要把多年归一化或新估值参数合回正式评分分支。

## 2026-07-14

### `ea00a73` · 现金流量表 FCF 取代净利代理并可见披露

- A 股从当前东财现金流同一报告行读取 `NETCASH_OPERATE` 和 `CONSTRUCT_LONG_ASSET`，只在期间一致且资本开支有效时生成 `free_cash_flow = OCF - cash capex`。年度历史、来源字段、期间和衍生 basis 均显式输出；缺 capex 时不猜测 FCF。
- US 股优先消费 yfinance cashflow 的 `Free Cash Flow`，缺该行时才以同列 `Operating Cash Flow + signed Capital Expenditure` 重建。负 FCF 保持为负，不允许用正净利 fallback 制造 DCF。
- 估值端优先使用实际/现金流表衍生 FCF；只有 FCF 完全缺失时才保留已标记的净利×0.8 fallback。输入为非正时 DCF 和敏感度矩阵均不生成。
- 修复跨市场币种误导：AAPL DCF 从硬编码 `¥` 改为 `US$`，并在 HTML 估值卡可见展示“现金流量表 FCF/净利代理”、期间、输入值、币种和警告；所有文本做 HTML 转义。
- 同日真实数据对比（DCF 增长/WACC 假设不变）：
  - `600519.SH`：净利代理输入 `658.56亿` → 实际 FCF `583.95亿`；DCF `14528.0亿` → `12882.0亿`，约 `-11.3%`。
  - `688017.SH`：代理 `0.99亿` → 实际 FCF `0.52亿`；DCF `21.9亿` → `11.5亿`，约 `-47.5%`；六年 FCF 中有两年为负，不再被利润代理遮盖。
  - `AAPL`：代理 `896.08亿 USD` →现金流量表 FCF `987.67亿 USD`；DCF `19767.7亿` → `US$21788.2亿`，约 `+10.2%`。
  - `MSTR`：实际 FCF `-225.8亿 USD`，明确返回 DCF 不适用；不生成零值敏感度表或任何正估值。
- 真实基金富化补验：`600519.SH` 在 `993` 源行/`671` 主动基金上设 hard cap=`2`，只发出预算内 4 次调用，完整富化 2 家、保留 669 家 lite，总耗时 `2.2–2.9s`。
- 验证：scoring `36/36`、branch harness `35/35`、builder `28/28`、flow/data-contract/render disclosure `22/22`、school `9/9`、registry `6/6`、fund runner `7/7`、fund lite/rendering `11/11`、mutual-fund classification `6/6`，共 `160/160`；`py_compile`、`git diff --check` 和 lite/medium 缓存篮子通过。
- 最终对照 baseline=`f63f9b8`、candidate=完整代码树：`64 raw + 7 synthetic = 71`，结果 `71 ok / 0 review / 0 possible_regression`，分数与交易档位变化均为 0。
- 纯评分三轮为 `2.124/2.226s`、`4.614/4.502s`、`2.660/2.607s`；中位数 `2.660/2.607s`，候选约快 `2.0%`，三轮均无告警。只判定“无性能回退”，不把运行顺序/文件系统缓存差异宣称为稳定提速。
- 公正效果评分 `9.6/10`。剩余风险是当前 DCF 仍为单期输入的简化增长/WACC 模型；FCF 口径、多年归一化、FCFF/FCFE 和净债务桥接存在模型语义冲突，未经 shadow 对比不应继续自动调参。

### `952342d` · 真实数据契约补齐与长循环硬边界

- 用当日真实东财/AkShare 返回发现 OCF schema 已漂移为 `NETCASH_OPERATE`；旧实现会静默返回空 OCF，且有将最新季度 OCF 除以最新年度净利的虚假期间精度风险。新契约同时兼容中英字段、按报告日排序、区分季报/年报，并只在同一财年年报 OCF 与净利间计算现金含量。
- 真实 `600519.SH` 回放：修复前 OCF 为空；修复后最新 2026Q1 OCF `269.1亿`，2025 年度 OCF `615.22亿`，与同年净利的比率 `0.75`。输出明确为 OCF，没有创建 `fcf` 或 `fcf_margin`。
- 估值输出增加来源、匹配方法和输入行业诊断；缺行业时 cninfo 跨行业参考仍不写入 `industry_pe`。真实 `688017.SH` 返回 PE `505.59`、PB `19.58`、`industry_pe=—`，市场 PE 参考 `33.2` 仅披露。既有 DCF 公式未调参，但现明示标记为 `净利×0.8` 代理输入，不得解读为实测 FCF/OCF 或精确内在价值。
- 真实 `600519.SH` 基金持仓源返回 `993` 行：`671` 个主动基金进入 lite 列表，`322` 个被动/指数基金过滤，零完整统计网络调用时 `0.746s`。新增默认 hard cap `50`、worker 上限 `8` 和调用预算诊断；只有显式 `UZI_FUND_ALLOW_UNBOUNDED_STATS=1` 才能越过上限，从控制面阻断 859/993 式长循环回归。
- 真实证券路由：`510300.SH` 识别为 ETF 并返回 10 个真实持仓；`110011` 识别为开放式基金并返回 10 个真实持仓。root `run.py 110011 --depth lite --no-open-report` 现以专用 `PipelineFallback` 预期分流到 legacy，退出码 `0`、无 traceback，且没有启动股票 pipeline。
- 官方事件 overlay 刷新至 `as_of=2026-07-14`：SMCI 仍只有 Rule `5250(c)(1)` 明确闭环，两条 Item 4.01 仍 unknown；HUBG 的 Item 4.02/3.01 均未闭环；AAPL 仍为 gap。因没有新的精确 issuer+同规则/事件族+官方终局语句，本轮刻意不扩展生命周期关键词。
- 验证：`py_compile` 和 `git diff --check` 通过；scoring `36/36`、branch harness `35/35`、builder `28/28`、flow `18/18`、school `9/9`、registry `6/6`、fund runner `7/7`、fund lite/rendering `11/11`、mutual-fund classification `6/6`，共 `156/156`；lite/medium 缓存篮子通过。未重装、未跑 deep、未运行 update。
- 最终中立对照 baseline=`55580d0`、candidate=本次代码树：`64 raw + 7 synthetic = 71`，分布为 core `10`、holdout `6`、official overlays `32`、synthetic raw `16`、synthetic feature `7`。结果 `71 ok / 0 review / 0 possible_regression`，所有评分与交易档位变化均为 `0`。
- 纯评分三轮 baseline/candidate 为 `2.186/2.645s`、`2.151/2.085s`、`2.192/2.177s`；中位数 `2.186/2.177s`，候选约快 `0.4%`，三轮均无性能告警，中立结论为性能持平。
- 公正效果评分 `9.5/10`：本轮关闭了前次三个真实网络残余风险中的 OCF/估值和基金长列表，且评分边界零漂移。扣分项是 DCF 仍只是已明示披露的简化代理，以及未建立真实公网 Cloudflare tunnel（避免在验证中无必要暴露本地报告）。

## 2026-07-13

### `f8f235b` · 官方事件解决态闭环与真实 SEC 生命周期复验

- 将 `resolution_status` 从可自报字段收紧为可验证证明：必须存在更晚的官方记录、精确 issuer、同一窄生命周期主题、不同 source record、匹配 canonical event、非未来日期；SEC archive 还必须解析到同一 EDGAR CIK。自引用、同 URL、跨 CIK、伪造、未来和无证明的解决声明全部继续按 active 风险处理。
- builder 只对高精度的 Nasdaq Listing Rule `5250(c)(1)` 周期报告合规生命周期自动关联；明确要求后续 8-K 同时出现“now complies”与“matter is now closed”。延期、补交计划、临时 exception 仍是 active；处罚、欺诈、财报不可依赖、审计师变更和泛化 remediation 不自动关闭。
- 真实在线复验以 `as_of=2026-07-13`、`lookback_days=730` 顺序抓取 SEC 官方页并冻结：
  - SMCI 2024-09-20/2024-11-20 的 Rule 5250(c)(1) 不合规通知及 2024-12-06 临时 exception，被 2025-02-26 后续 8-K 精确关闭，共关联 3 条；两个 Item 4.01 审计师变更仍为 active P1。
  - HUBG 为 `ready/high` 但该窄主题 `no_match`；AAPL 为 `gap/low`，未从无证据推断事件或解决态。
  - 12 个公开官方 overlay 现作为可复现冻结输入跟踪入库；不含 key、cookie、authorization 或其他凭据。
- branch harness 对混合 active/resolved overlay 新增两类影子：原样风险样本继续检验未解决事件，拆出的 verified-resolution 样本只检验“不误伤”，不会因历史事件获得正向奖励。
- 最终对照：baseline=`d187f54`，candidate=`f8f235b` 对应代码树；core + holdout + discovered cache + frozen overlays + synthetic adversarial，`64 raw + 7 synthetic = 71`，lite/medium 均跑。结果 `71 ok / 0 review / 0 possible_regression`，所有评分漂移与档位变化为 0。
- 真实 SMCI 反事实：仅已关闭 3.01 注入 AAPL 时为 `68/buy_candidate`、事件维度 `5`；保留未解决 4.01 时为 `64.9/watch`、事件维度 `4`。SMCI 最小原样为 `64.4/watch`；其 resolved-only 影子事件维度回到 `5`。这证明“解决态不误伤”和“未解决风险仍阻止高置信买入”同时成立。
- 验证：scoring consistency `36/36`、branch harness `35/35`、overlay builder `28/28`、flow `15/15`、registry `6/6`、fund renderer `9/9`、school scores `9/9`，共 `138/138`；`py_compile`、`git diff --check`、lite/medium 缓存篮子通过。venv 无 pytest，未重装、未跑 deep、未运行 update。
- 性能：正式报告单次为 `1.697s -> 1.807s`（候选慢 `6.5%`）；同一正式 commit 连跑三次的中位数为 `1.697s -> 1.696s`（约 `-0.1%`），单次方向在 `-5.8%` 到 `+6.5%` 间波动，三次均 `0` performance warning。中立结论是无可测性能回退，也没有可宣称的稳定优化收益。
- 公正评分 `9.4/10`：真实官方输入、同一冻结输入、身份/时间/主题防伪和交易非伤害均闭环。剩余风险是当前自动生命周期只覆盖一个高精度 SEC 规则主题，A/HK 和 Item 4.01 等必须先找到同样明确的官方终态语句后再 shadow 扩展，不能泛化关键词。

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
