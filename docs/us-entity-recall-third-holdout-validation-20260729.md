# US entity recall 第三批真实 holdout 验证（2026-07-29）

## 结论

本轮值得保留，但理由不是“继续扩大 alias”，而是第三批真实负控发现了两个此前未覆盖的短 ticker 污染：

- `NU` 会把 `Nu Skin Enterprises (NUS)` 的标题归给 `Nu Holdings (NU)`。
- `T` 会把 `T. Rowe Price (TROW)` 的标题归给 `AT&T (T)`。

最小修复把 `NU/T` 的裸 ticker 降为不可信，仅接受带证券语境的 ticker 或发行人官方绑定的完整实体。150 条真实 Yahoo 标题上，precision 从 `86.67%` 提升到 `100%`，recall 保持 `100%`，跨发行人污染率从 `12.82%` 降到 `0`。真实生产复跑又排除了 Shift4 前 CEO/SpaceX 新闻和以 D-Wave 为主语、AT&T 仅为交易对手的两条新闻；FOUR 与 T 的评分、交易档位均未变化。

不建议继续增加 MARA 旧名、FOUR 普通词或创始人姓名 alias：当前没有稳定 false negative，扩张收益未被证明，污染面反而更大。

## 状态与边界

- 隔离分支：`codex/scoring-validation-us-entity-recall-shadow`
- 正式基线：`48e20fc4c9fe9823ab055155511be3bc503cb78b`
- 候选代码检查点：`91cb6eb22f8cac4970617c8036c5b3bc022426df`
- `origin/codex/scoring-validation-guardrails` 仍为正式基线；本轮不自动合回。
- `upstream/main=fce996c33e70eddce8e375f53cd252b549eb3d7c`；upstream push URL 保持 `DISABLED`。
- `main`、`codex/windows-local-stable` 未修改。
- 未重装依赖，未跑 deep，未运行 update，未改评分权重、动量参数、P0/P1 阈值或估值参数。
- 没有真实 SEC 联系身份，因此生产采集没有发 SEC 请求并记录 access gap；MARA 身份绑定使用发行人自有 IR 域名上的 8-K 镜像。CBOE 零请求。

## 真实样本与选择理由

Yahoo `day_gainers`、`most_actives` 与 chart v8 在同一时点筛选，并对 10 个不同命名难度标的各取当前新闻：

| 标的 | 命名/污染压力 | 真实动量概况 |
|---|---|---|
| NU | 两字符 ticker；Nubank 品牌与 Nu Holdings 法人名不同；邻近发行人 Nu Skin | 1m `+10.33%`，3m `-0.75%`，6m `-20.08%`，1y `+15.23%` |
| MARA | MARA Holdings 由 Marathon Digital Holdings 更名 | 1m `-19.05%`，3m `+5.28%`，6m `+17.94%`，1y `-31.41%` |
| T | 单字符 ticker；邻近发行人 T. Rowe Price | 1m `+7.48%`，3m `-4.31%`，6m `+4.14%`，1y `-11.52%` |
| SOFI | 品牌大小写与法律后缀变化 | 1m `-5.59%`，3m `-10.02%`，6m `-34.57%`，1y `-19.70%` |
| JBLU | JetBlue 品牌短于法人名；同时进入涨幅与活跃榜 | 1m `-9.50%`，3m `+9.92%`，6m `+6.89%`，1y `+24.54%` |
| INTC | 高成交半导体；跨发行人新闻密度高 | 1m `-28.56%`，3m `+7.86%`，6m `+115.74%`，1y `+343.28%` |
| NOK | 美国 ADR 与海外法人名 | 1m `-28.67%`，3m `-13.75%`，6m `+34.30%`，1y `+117.84%` |
| FOUR | 普通词 ticker；Shift4 品牌；前 CEO 新闻压力 | 1m `+4.87%`，3m `+11.04%`，6m `-22.17%`，1y `-53.02%` |
| CLS | 供应商/客户链新闻污染压力 | 1m `-5.72%`，3m `-24.63%`，6m `+3.24%`，1y `+83.56%` |
| RGEN | 独特法人名、低污染的召回控制 | 1m `-10.85%`，3m `+10.80%`，6m `-19.76%`，1y `+9.54%` |

初始 ticker 查询 100 条；为避免 ticker 搜索天然隐藏别名漏召回，shadow 工具增加可复现的 `search_queries`，再加入 Nubank、Marathon Digital Holdings、Nu Skin、T. Rowe Price 与 `four stocks` 的真实 Yahoo 反向检索。按发行人内去重后共 150 条，重复率 `0`。

其中明确相关 65 条、明确无关 67 条、歧义 18 条。歧义包括隐藏成分股的篮子标题和只涉及高管个人观点的标题；`relatedTickers` 从不单独决定标签。

## alias 来源与发行人绑定

仅加入下面三项生产身份：

| ticker | alias | 来源 | 绑定规则 |
|---|---|---|---|
| NU | `Nu Holdings` | `https://www.investidores.nu/financials/filings/` | Nubank 官方 IR 的 filings 页面明确面向 Nu Holdings 股东 |
| NU | `Nubank` | `https://international.nubank.com.br/company/nubank-to-invest-r-45-billion-in-brazil-in-2026/` | 发行人控制的 Nu International 新闻把 Nubank 业务与 Nu Holdings 业绩明确绑定 |
| T | `AT&T` | `https://investors.att.com/resources/faqs` | AT&T 官方 IR 明确 AT&T 在 NYSE 的 ticker 为 T |

MARA 的前法人名已由发行人 IR 域名 8-K 证明，但第三批真实集没有产生无 ticker 的稳定 false negative，因此只保留为 shadow 候选，没有加入生产 registry。创始人/CEO 姓名仍不作为 alias。

## precision / recall / 污染率

| 指标 | 修改前 | 修改后 |
|---|---:|---:|
| TP | 65 | 65 |
| FP | 10 | 0 |
| FN | 0 | 0 |
| precision | 86.67% | 100% |
| recall | 100% | 100% |
| 跨发行人污染率 | 12.82% | 0 |
| 重复率 | 0 | 0 |
| 新鲜度中位数 | 0.61 天 | 相同 |
| 新鲜度 P95 | 22.57 天 | 相同 |
| 7 天 / 30 天内比例 | 91.33% / 97.33% | 相同 |
| 查询延迟中位数 | 0.23 秒/发行人 | 相同输入 |
| 查询延迟 P95 / 最大值 | 0.88 / 0.88 秒 | 相同输入 |

### false positive 摘要

修复前 10 条、修复后 0 条：

- NU→NUS 共 4 条：Nu Skin 财报预告、Nu Skin 涨幅、两条包含 Nu Skin 的行业/精选标题。
- T→TROW 共 6 条：T. Rowe Price 财报预告、区间基金、私募市场基金、加密 ETF、市场表现和下一周财报标题。

真实生产流另发现并排除：

- FOUR：NASA Chief / Elon Musk / SpaceX；Shift4 只出现在摘要的“former Shift4 Payments (NYSE: FOUR) CEO”身份说明中。
- T：两条以 D-Wave 为投资主体、AT&T 仅为 deal/agreement 对手方的新闻。

### false negative 摘要

修改前后均为 0。`Nu Holdings`、`Nubank (NU)`、`AT&T`、合格 ticker 语境均保留。没有为了追求表面召回而放宽 substring。

## 真实生产 lite / medium

均使用项目 venv、`--no-resume --no-browser` 和当次真实数据：

| 标的 | 深度 | 分数 | 结论 | 事件净化 |
|---|---|---:|---|---|
| NU | medium | 51.6 | 观望偏空 | 6 条；Nu Holdings/Nubank 召回保留，0 Nu Skin |
| MARA | medium | 42.5 | 谨慎 | 8 条；当前/前法人名标题均保留 |
| T | lite | 47.6 | 谨慎 | 7→5 条；移除 2 条 D-Wave 主体新闻 |
| FOUR | lite | 44.1 | 谨慎 | 7→6 条；移除前 CEO/SpaceX 新闻 |

四份报告均 `critical=0`。事件净化前后 T/FOUR 分数与档位不变。

与上一轮 KNSA `66.9`、OSCR `46.2`、ITRI `59.0`、MSTR `36.3` 相比，本轮结果仍体现“热门或单日上涨不等于买入”：

- NU 只有 1 个月动量为正，6 个月为负，51.6 的观望偏空合理。
- MARA 6 个月反弹但 1 个月和 1 年明显为负，42.5 没有把加密/AI 叙事当成质量。
- T 的中长期动量弱，47.6 没有因频繁交易对手新闻被抬高。
- FOUR 3 个月转强但 1 年仍跌逾 50%，44.1 反映反弹与长期破坏并存。

## 分支对照、事件护栏与性能

- baseline：`48e20fc4c9fe9823ab055155511be3bc503cb78b`
- candidate：`91cb6eb22f8cac4970617c8036c5b3bc022426df`
- `72` 个冻结 raw（含新增 NU/MARA/T/FOUR，lite+medium）+ `7` 个对抗样本
- 结果：`79 ok / 0 review / 0 possible_regression`
- 评分变化：全部 `0`
- 交易档位变化：全部 `0`
- active 官方 P0/P1 仍阻止不合理买入；伪造、已解决、过期、cross-issuer 事件不误伤
- MU 不匹配 Musk；NU 不匹配 Nu Skin；T 不匹配 T. Rowe Price；前 CEO 和反向 deal 不回流
- direct runner：`113/113`
- `py_compile`、`git diff --check`：通过
- 正向耗时：`3.1s -> 2.6s`
- 交换顺序：`2.0s -> 2.0s`
- performance warning：0；只判“无性能回退”，不宣称提速

真实 Yahoo/生产数据用于效果判断；冻结 synthetic 只补充 P0/P1、防伪、过期和边界回归门，不替代真实效果证据。

## 是否值得合回

建议吸收候选代码，但仍按用户要求不自动合回正式分支。理由：

1. 真实污染模式稳定且可由相邻发行人解释。
2. 修复后 precision 与污染率净改善，recall 不下降。
3. 生产事件流同步净化，评分与档位不漂移。
4. 79/79、0 possible regression、无性能回退。

## 停止线

- 不把 MARA 前名加入生产，除非独立真实集出现无 ticker 的重复漏召回。
- 不因 `FOUR` 是普通英语词就直接加入通用集合；本轮真实检索没有证明该污染。
- 不加入创始人、CEO、产品高管姓名 alias。
- 不扩大 `deal/partner/supplier/former executive` 为宽泛否定词，只保留有明确语法方向的排除。
- 不把 `relatedTickers` 当发行人证据。
- 不接入 SEC，直到配置真实联系身份；不联网 CBOE。
- 不改评分、动量、P0/P1 或估值参数。

## 下一步模型

下一步不是继续扩 alias，而是独立合并审计：

- 默认：`GPT-5.6 Terra` + `中推理`，复核标签、官方绑定和正式分支文件重叠。
- 只有正式分支发生代码冲突、或新真实样本暴露身份/事件消费冲突时：`GPT-5.6 Sol` + `高推理`。
