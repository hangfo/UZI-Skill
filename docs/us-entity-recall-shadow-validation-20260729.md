# 美股公司实体 alias / entity matching 真实召回 shadow 验证

日期：2026-07-29

隔离分支：`codex/scoring-validation-us-entity-recall-shadow`

正式基线：`codex/scoring-validation-guardrails@48e20fc4c9fe9823ab055155511be3bc503cb78b`

## 结论

值得吸收，但只吸收“发行人官方来源绑定的 alias + 常见词 ticker 的上下文限定”，不放宽裸 substring，不改评分、动量、事件阈值或估值参数。

冻结的 119 条 Yahoo 真实新闻中，基线为 `TP=51 / FP=6 / FN=7 / TN=43 / ambiguous=12`；候选为 `TP=57 / FP=0 / FN=1 / TN=49 / ambiguous=12`。precision 从 `89.47%` 提升到 `100%`，recall 从 `87.93%` 提升到 `98.28%`，跨发行人污染率从 `10.53%` 降到 `0`。唯一剩余 FN 是标题仅写“Markets brace for Fed decision and Big Tech earnings”的泛市场新闻；冻结 Yahoo query1 元数据没有 Meta、ticker 或受控品牌，继续 fail closed。

## 样本与选择理由

数据源为 2026-07-29 实时 Yahoo Finance search，每个 ticker 最多 10 条，冻结为：

- `MU / AI / C / F`：短 ticker，其中 `AI/C/F` 同时是普通英文词或单字母。
- `GOOGL / META / HOOD`：品牌名、法人名或股票代码不同。
- `ON / IT / CAT`：常见词或高歧义 ticker。
- `XYZ`：Square 更名为 Block，且 Cash App 是独立消费者品牌。
- `GEN`：NortonLifeLock 更名为 Gen Digital，包含 Norton、Avast、LifeLock、MoneyLion 等品牌或受控业务。

共 119 条，逐条人工标为 relevant、irrelevant 或 ambiguous，并由评估器分别映射为 `true_positive / false_positive / false_negative / ambiguous`。冻结快照重复率为 `0%`；Yahoo 请求延迟中位 `0.178s`、P95 `0.959s`；新闻年龄中位 `0.459 天`，`87.39%` 在 7 天内、`98.32%` 在 30 天内、`100%` 在 90 天内。

可复现文件：

- `local-ops/state/us-entity-recall-shadow/20260729-yahoo-real.json`
- `local-ops/state/us-entity-recall-shadow/20260729-yahoo-real-labels.json`
- `local-ops/state/us-entity-recall-shadow/20260729-yahoo-real-metrics.json`
- `tools/us_entity_recall_shadow.py`

## alias 来源与身份绑定规则

alias 不凭常识或字符串相似加入。每个 alias 必须带 `kind`、发行人官方 `source_url` 和明确 `binding`：

- C3.ai：C3 AI investor relations。
- Citi：Citigroup 官方新闻稿把 Citigroup Inc. `(NYSE: C)` 与 Citi 品牌绑定。
- Google：Alphabet investor relations 明示 Google 是 Alphabet 子公司。
- Facebook / Instagram / WhatsApp：Meta investor relations 的 Family of Apps 披露。
- onsemi：onsemi investor relations 把品牌与 `(Nasdaq: ON)` 绑定。
- Square / Cash App：Block investor relations 的更名公告和品牌清单。
- Gen / Norton / Avast / LifeLock / NortonLifeLock：Gen Digital investor relations 的更名与品牌公告。
- MoneyLion：Gen Digital investor relations 的已完成收购公告。

运行时规则：

1. 非歧义 ticker 仅做 token boundary 匹配，`MU` 不得命中 `Musk`。
2. `AI/C/F/IT/ON/CAT/GEN` 裸词不构成证据；只接受 `$TICKER`、`(TICKER)`、交易所前缀、`ticker stock/shares/earnings` 等证券上下文。
3. 法人名优先完整短语或真正有区分度的 token；`digital/technology/semiconductor/motor` 等通用后缀不单独命中。
4. alias 只从上述发行人绑定 registry 读取。
5. “vendor recognized/named in Gartner”“former Citi banker”“according to Gartner”等次要提及不得把另一发行人新闻纳入目标公司。
6. `Gen` 作为普通词风险过高，只接受发行人事件模板；Norton、MoneyLion 等已绑定品牌按完整 token 匹配。

## 逐条错误摘要

基线 6 条 FP：

- `AI`：BigBear.ai 财报标题因包含 `.ai` 被误收。
- `ON`：`Should You Climb On?` 把普通介词误作 ticker。
- `IT`：Tecnotree、Securden、Flexera、SoundHound 四条供应商新闻仅提 Gartner，被误作 Gartner 自身新闻。

基线 7 条 FN：

- `C`：Citi 贸易数字化方案。
- `META`：未出现实体名的泛 Big Tech 标题。
- `ON`：含 onsemi 的半导体多股新闻。
- `XYZ`：Cash App 消费者品牌新闻。
- `GEN`：Norton 两条、MoneyLion 一条品牌新闻。

候选消除全部 6 条 FP，并恢复 Citi、onsemi、Cash App、Norton、MoneyLion 共 6 条 FN；只保留 META 泛标题 1 条 FN。该 FN 没有足够冻结元数据，不应通过猜测或 query-result 位置强行召回。

## 生产与回归验证

- `AI --depth lite --no-resume`：真实生产完成，`critical=0`；仅保留 7 条 C3.ai 新闻，BigBear.ai 被排除；报告为 `skills/deep-analysis/scripts/reports/AI_20260729/full-report-standalone.html`。
- `GEN --depth medium --no-resume`：真实生产完成，`critical=0`；8 条事件均有 Gen Digital/GEN 明示实体；报告为 `skills/deep-analysis/scripts/reports/GEN_20260729/full-report-standalone.html`。
- `fetch_events.main("MU")`：实时保留 2 条 Micron 相关标题，`Musk` 命中数为 0。
- `py_compile` 通过；direct runner `108/108`，覆盖 common-word ticker、MU/Musk、active P0/P1、伪造、过期、resolved、cross-issuer 以及 branch harness 自检。
- 冻结 branch harness 为 `72 raw + 7 synthetic = 79`：`79 ok / 0 review / 0 possible_regression`，所有分数变化和交易档位变化均为 0。
- 最终 commit 正向顺序进程耗时 `3.878s -> 3.603s`，79 项纯计算中位 `0.004s -> 0.007s`；交换顺序为候选 `8.700s`、正式基线 `8.496s`，双方项中位均为 `0.011s`。两轮 performance warning 均为 0；纯评分代码未修改，进程总时长受当时机器负载影响明显，只判定没有稳定性能回退，不宣称提速。

branch 对照报告：

- `local-ops/state/branch-score-compare/20260729-us-entity-recall-shadow-final.md`
- `local-ops/state/branch-score-compare/20260729-us-entity-recall-shadow-perf-swap.md`

## SEC / CBOE 边界

当前环境没有可核验的 SEC 真实联系信息，因此没有构造 User-Agent、没有请求 SEC，记录为 access gap。alias 身份绑定改用发行人官方 investor-relations 页面。CBOE 未获许可，本轮没有任何 CBOE 联网。

## 公允建议与停止线

建议把本隔离分支作为候选吸收到正式评分分支，但本轮不自动合回。收益来自同时提高真实召回和降低污染，且分数、档位、P0/P1 风险边界与性能均无回退。

停止线：

- 不为剩余 META 泛标题放宽 substring、publisher 名称或 Yahoo 查询位置推断。
- 不加入没有发行人官方来源和控制关系证明的产品名、简称、创始人名或历史品牌。
- 不把“提到研究机构/供应商/前雇主”当作发行人事件。
- 若新增 alias 在独立真实样本上产生任一跨发行人 FP，先回到 shadow，不进入生产。
- 本方向不触碰评分权重、动量参数、P0/P1 阈值和估值参数。

下一步建议：使用 `GPT-5.6 Terra + 中推理` 做独立时点的 Yahoo 复采与标注复核；只有新样本暴露发行人关系或事件消费链的重叠问题时，再使用 `GPT-5.6 Sol + 高推理` 做生产变更。
