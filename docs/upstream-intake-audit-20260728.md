# 三方上游择优吸收审计（2026-07-28）

## 结论

本轮应吸收两项用户级补充 Skill release，并只把一个经真实端点证明的北交所路由修复带入 UZI：

- `a-stock-data`：从官方 `v3.4.0` 升到 `v3.5.1`，但官方分页修复仍假设每页 200 条；当前东财实际每页只给 100 条。安装后保留最小本地补丁 `v3.5.1+uzi.1`，按首屏实得页长翻页。
- `global-stock-data`：从官方 `v1.0.1` 精确升级到 `v2.0.3`，不加本地补丁。
- `UZI-Skill`：正式评分基线已经包含 `upstream/main=fce996c`，当前为 `ahead 62 / behind 0`，不重复 merge。只修复由本轮真实交叉检查发现的 UZI 内部 `920xxx` 行情 transport 前缀漂移。

没有复制板块资金流、FINRA、CBOE、SEC Frames、Treasury 或 CFTC 示例到 UZI 生产流水线，也没有调整评分、交易档位、估值参数、重试次数或并发。

## 版本真值

| 项目 | 审计前本地 | latest release | release commit | HEAD | 处理 |
|---|---|---|---|---|---|
| `simonlin1212/a-stock-data` | `v3.4.0`，与旧 tag 字节一致 | `v3.5.1` | `281fc69` | `281fc69` | 升级并加已审计分页补丁 |
| `simonlin1212/global-stock-data` | `v1.0.1`，与旧 tag 字节一致 | `v2.0.3` | `c0b3ed8` | `c0b3ed8` | 精确升级 |
| `wbh604/UZI-Skill` | 正式分支已含 `fce996c` | `v3.9.1` | tag 指向 `337d502` | `fce996c` | 无待合入 commit |

`UZI-Skill v3.9.1` 与 `upstream/main=fce996c` 不是同一个点。HEAD 在 release 之后包含 root `SKILL.md` 入口和 flow/data-contract 修复；这些 ancestry 已在此前的隔离 merge 中进入正式评分分支。本轮不 cherry-pick、不制造第二次冲突。

## 变化、重叠与取舍

### a-stock-data v3.4.0 → v3.5.1

| 上游变化 | 真实/静态证据 | UZI 重叠 | 决定 |
|---|---|---|---|
| 5 前缀 ETF、指数、`920` 北交所、显式 `sh/sz/bj` 路由 | `510300→sh`、`000016→sh`、`920002→bj`；显式前缀保持 | UZI canonical router 已覆盖，但两个直连 provider 复制了旧规则 | Skill 全收；UZI 只统一 transport 前缀 |
| 腾讯 A 股 `f44/f45` 市值字段纠正 | `920002/688146/601127` 返回总/流通市值且量级合理 | UZI 已是 `f44=流通、f45=总市值` | 不重复改 |
| 通达信空/非标准 payload 校验与腾讯分钟 K 兜底 | 代码契约和 fenced-block 编译通过 | UZI 不消费该独立 helper | 留在补充 Skill |
| `board_fund_flow` 与分页 | 东财报告 `total=496`，但 `pz=200` 时每页实得 100；上游会在 200 条提前退出 | UZI 没有板块资金流生产消费者 | Skill 保留 `+uzi.1` 修补；不接 UZI |
| README、计数和营销文本 | 不影响数据契约 | 无 | 舍弃为生产变更理由 |

本地补丁不是 fork：补丁清单固定在
`local-ops/patches/stock-skills/a-stock-data-v3.5.1-uzi.1.patch`，更新器只在“latest 基版仍为 3.5.1 + 本地 SHA256 精确命中”时保护它；未来新 release 会正常替换，再由真实 smoke 决定补丁是否删除。

### global-stock-data v1.0.1 → v2.0.3

| 上游变化 | 价值 | 决定 |
|---|---|---|
| CBOE options/Greeks/0DTE | 数据细，但存在单独使用条款与授权边界 | 安装文档能力；未授权不联网、不进生产 |
| FINRA daily short volume | 可作短售活动补充，但不等于 short interest | 只作人工/shadow 证据，不加分 |
| SEC daily filings/full-text/Frames | 官方源价值高；Frames 仍需 taxonomy、单位、期间和 issuer 映射 | 保留补充 Skill；SEC 无真实 contact 时 fail-closed |
| Treasury/CFTC/Nasdaq calendar | 宏观与事件日历有用 | 按需查询，不复制成默认 fetcher |
| Tencent US/HK 字段、SEC Frames instant suffix、OCC 数字 root 修复 | AAPL、00700 与数字 root 实测/边界验证通过 | Skill 全收；UZI 现有公共 quote 字段实测正常，不改写 |
| v2.0.3 任意 Frames fallback | 提高探索覆盖 | 不直接变成估值/评分输入，避免错 tag 和伪精度 |

### UZI release/HEAD

`fce996c` 的 direct report、remote 清理、OCF/FCF 隔离、估值 fail-closed、fund/report 路由和 registry schema 已经完成过冻结输入验证并进入当前 ancestry。本轮审计没有发现新的 upstream commit。

新增 UZI 修复的因果链：

1. `parse_ticker("920002")` 正确得到 `920002.BJ`。
2. `_fetch_price_tencent_qt` 却独立拼成 `sz920002`，direct provider 拼成 `sh920002`。
3. 真实腾讯/新浪均只对 `bj920002` 返回有效行情。
4. 新增 `a_share_transport_prefix()`，所有直连路径从 canonical router 派生，消除三套前缀表的漂移。

这不改变评分边界，只把此前不可达的真实北交所报价恢复出来。

## 真实验证

### Skill 结构与端点

- `a-stock-data`：48/48 Python fenced blocks 编译。
- `global-stock-data`：35/35 Python fenced blocks 编译。
- 腾讯 A 股：`920002` 万达轴承、`688146` 中船特气、`601127` 赛力斯均得到真实价格和总/流通市值。
- 腾讯跨市场：AAPL 得到 USD 报价、市值、PE/PB；`00700.HK` 得到 HKD 报价、市值、PE/PB。
- FINRA：最新文件 `20260727`，12,108 个 symbol；AAPL short-volume ratio `0.4025`。
- Treasury：最新记录 `2026-07-27`，10Y `4.65`、2Y `4.31`。
- CFTC：真实目录返回 3 项。
- SEC：Frames 期间后缀可识别 `CY2025Q1I/CY2025Q4I`；未配置真实联系信息时按契约拒绝请求。
- OCC：`NVDA1` 数字调整 root 和标准 `AAPL` 均可解析。
- CBOE：`network_called=false`，没有用测试绕过授权边界。

完整机器可复现输出：
`local-ops/state/upstream-audit/20260728-stock-skills-real-smoke.json`。

### 北交所 UZI 修复

同一时刻真实结果：

| 路径 | 修复前 | 修复后 |
|---|---|---|
| canonical ticker | `920002.BJ` | 不变 |
| data source 腾讯 | `{}`（误发 `sz920002`） | 万达轴承 `50.69`，总市值 `32.29亿`，流通 `22.61亿` |
| direct Tencent | short response（误发 `sh920002`） | `source=tencent_qt:bj920002`，价格 `50.69` |
| direct Sina | 空 | `source=sina_hq:bj920002`，价格 `50.69` |

价格是抓取时快照，不作为未来价格声明；验证目标是代码、交易所前缀和字段契约。

## 持续吸收机制

1. 定期只运行 `update-uzi.ps1 -Mode Audit`；它读取 latest release、release commit、HEAD 和 commits-after-release，不改文件。
2. 下载锁定 release 解析出的 immutable commit SHA，避免 tag 检查与下载之间发生漂移。
3. 用户级 Skill 先比对本地/旧 tag 哈希；再编译全部代码块并对新增端点做小批量真实 smoke。
4. 本地补丁必须有基版、精确哈希、复现证据和删除条件；无法验证的 `+uzi` 文件在 Apply 时不会被静默保护。
5. UZI upstream 永远从正式检查点开隔离分支，以 merge 保留 ancestry；重叠文件做语义合并。
6. 生产接入新数据源前先跑 shadow：覆盖率、字段完整率、时效、跨源误差、延迟和条款许可都通过，才讨论消费端。
7. 最后用同一冻结输入跑 lite/medium、真实 overlay、synthetic adversarial 和多轮性能门禁；零 `possible_regression` 才能 fast-forward 正式分支。

## 冻结评分与性能门禁

baseline=`6b295bd`，candidate=`5cb1323`。输入为 `64` 个 core/holdout/discovered-cache/frozen-overlay raw cases，加 `7` 个 synthetic adversarial cases；raw 全部同时跑 lite 与 medium。

- `71 ok / 0 review / 0 possible_regression`。
- 所有 investment score、overall score、fundamental score、panel consensus 和交易档位变化均为 `0`。
- structured active P0/P1、缺财务但主题热、游资热但机构卖出继续受限；伪造、已解决、过期和非 issuer 事件继续不误伤。
- 三轮交换顺序的整批进程耗时中位数：baseline `2.6s`，candidate `2.3s`。单轮范围分别为 `2.3–4.1s` 与 `2.2–4.6s`；存在 Windows 进程启动噪声，只能判定“无性能回退”，不宣称提速。
- direct runner `269/269`、`py_compile`、`git diff --check` 通过；项目 venv 无 pytest，未安装。

完整逐行结果：
`local-ops/state/branch-score-compare/20260728-upstream-intake-final.md`。

## 剩余风险与停止线

- 东财在首轮重试中出现短时断连，随后真实复跑成功返回 `total=496 / rows=205`；这既验证了补丁，也证明外部可达性会波动。不得把断连改成默认值。
- `board_fund_flow` 尚无 UZI 消费需求；在缺少收益归因前不得接入评分。
- FINRA short volume 不能冒充未平仓空头；SEC Frames 不能按名称相似直接进入 FCFF/DCF。
- CBOE 在取得明确授权前不运行网络 smoke，也不作为默认源。
- supplemental Skill 是 Markdown 可执行示例，不是稳定 Python package API；UZI 若未来接入必须重写为小型 schema adapter，而不是复制整段代码。
- 本轮只验证路由和数据契约收益，不声称这些数据能提高投资收益；评分和交易阈值保持冻结。
