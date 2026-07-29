# SEC 访问硬化、Yahoo 行情新鲜度与真实美股验证（2026-07-29）

## 公允结论

本轮值得吸收的是两项基础设施修缮，不是评分调参：

1. SEC 官方读取改为默认离线，只有显式 `--allow-network` 且
   `UZI_SEC_USER_AGENT` 含真实可联系邮箱时才允许请求。当前机器没有该身份，
   因而真实 SEC 请求为 0，缺口被明确保留；没有伪造联系人。
2. 真实生产验证发现 yfinance 对 INTC、SOFI 的日线尾部落后 Yahoo chart v8
   一个已完成交易日。候选实现保留 yfinance 的复权历史，只从 Yahoo v8 的
   5 日短尾部追加“日期严格更新”的记录，同日数据绝不覆盖。

CBOE 仍为 0 请求、0 路由、0 生产依赖。书面许可和具体产品使用范围确定前，
不应添加所谓 license-ack 环境变量来绕过治理。

## 官方合规依据与配置

- SEC 的公开 EDGAR API 不需要 API key，官方说明实时 JSON 与 bulk archive：
  https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC 允许自动化访问，但要求声明 User-Agent，当前公开上限为合计每秒 10 次：
  https://www.sec.gov/about/webmaster-frequently-asked-questions
- 本项目留出余量，按 sec.gov host 串行限制为每秒 8 次，并处理 429 /
  Retry-After、gzip 和 deflate。
- Cboe 的正式路径是先签 Global Data Agreement，再按产品/用途完成 onboarding：
  https://www.cboe.com/market_data_services/document_library

Windows 用户级配置示例（必须把示例替换为本人真实姓名和真实邮箱）：

```powershell
[System.Environment]::SetEnvironmentVariable(
  "UZI_SEC_USER_AGENT",
  "真实姓名 real-email@example.com",
  "User"
)
```

关闭并重新打开 Codex/终端后验证：

```powershell
$env:UZI_SEC_USER_AGENT
D:\UZI-Skill\.venv\Scripts\python.exe tools\evidence_overlay_builder.py `
  --ticker AAPL --target missing_financials --allow-network --no-write
```

不要把真实身份提交进 `.env`、`.env.example`、测试 fixture、日志或 Git。未配置时，
显式联网命令应在任何 SEC 请求前 fail closed；默认命令保持离线。

## CBOE 逐步办理流程

1. 先写清用途：仅人工研究、内部非展示、展示、衍生指标、历史回测或再分发。
2. 列出真正需要的产品和字段：期权链、Greeks、IV、0DTE、实时/延迟、历史深度。
3. 向 Cboe Market Data Services 提交用途和主体信息，索取适用协议/附表。
4. 完成 Global Data Agreement 和产品 onboarding，确认用户数、设备数、地域、
   保存期限、展示/非展示、衍生数据及再分发权利。
5. 取得书面授权后，把允许的产品、用途、生效/到期日和联系人放入本地受控配置；
   凭证进入 secret store，不进入仓库。
6. 再单独开发 host allowlist、速率限制、缓存期限、审计日志和到期 fail-closed；
   先 shadow，不直接进入评分。
7. 在许可到期、用途改变或产品超出附表时自动停用。

没有完成第 4–5 步前，本项目的正确状态就是“不联网”，不是功能缺陷。

## 真实生产样本

样本来自 2026-07-29 Yahoo most-active / gainers / losers，刻意覆盖不同风险形态，
且均从无缓存生产入口运行：

| 股票 | 选择理由 | 深度 | 综合分 | 投资分/档位 | Stage | 结果 |
|---|---|---:|---:|---:|---|---|
| INTC | 大成交量、单日急跌的大盘半导体 | medium | 44.9（旧尾部）/43.4（新尾部 shadow） | 43.5 / 回避 | 2 | 档位不变 |
| SOFI | 热门金融科技、下跌趋势护栏 | medium | 46.5/44.5 | 49.9 / 回避 | 4 | 档位不变 |
| JBLU | 财报后约 +10.5% 的航空股 | lite | 44.3 | 39.3 / 回避 | 2 | 热度未推成买入 |
| AMKR | 财报后约 -24.7% 的半导体股 | lite | 43.6 | 52.9 / 谨慎 | 1 | 不抄底升级 |
| GLW | 最新跌幅压力样本；修复后全新抓取 | lite | 44.0 | 57.9 / 观察 | 1 | `critical=0` |
| ONDS | 最新活跃小盘动量样本；修复后全新抓取 | lite | 46.9 | 51.1 / 谨慎 | 1 | `critical=0` |

INTC 的尾部从 2026-07-27 / 91.67 补到 2026-07-28 / 86.30；SOFI 从
2026-07-27 / 16.88 补到 2026-07-28 / 16.74。Stage、投资分和交易档位均未变化，
但综合判断更及时、更谨慎。GLW/ONDS 的新生产采集分别约 4.8s/4.3s。

## 事件实体复核

前轮三批 349 条真实 Yahoo 冻结集的正式结论保持：
`TP=166 / FP=0 / FN=1`，precision `100%`，recall `99.40%`，
跨发行人污染 `0`，重复率 `0`。本轮没有放宽 substring，也没有新增 alias。

新增观察：JBLU 流中出现标题
“Boeing Beats on Cash Flow, Books New Charge on Air Force One”，摘要同一视频确实
提及 JetBlue earnings。按发行人标题它是低相关/ambiguous，而非稳定 alias 漏召回。
单个联合视频不足以支持全局“标题必须含发行人”的修改，因为该规则会误杀并购、
客户、供应链和同业联动。停止线是：先累计独立样本；若同类联合内容稳定造成
跨发行人污染，才新增“主标题实体优先级”shadow 特征，不直接删新闻或改分。

## 冻结分支、边界与性能

- 正反顺序均覆盖 `98 raw + 7 synthetic = 105` 项，结果均为
  `105 ok / 0 review / 0 possible_regression`。
- 所有同输入评分和交易档位变化均为 0。
- active P0/P1 继续阻止不合理买入；伪造、已解决、过期和 cross-issuer
  反事实均未误伤；MU/Musk、常见词 ticker 和 substring 边界由 direct tests 覆盖。
- direct runner `216/216`；`py_compile` 和 `git diff --check` 通过。
- 纯评分前后交换顺序都无性能告警。Yahoo v8 新鲜度检查每股只取 5 行，
  8 股实测中位约 0.483s、最大约 0.553s；相对原 2 年 501 行请求减少约 99% 行数。
  这是采集精度成本，不进入纯评分路径。

## 历史 walk-forward 与上一轮对比

新增 INTC/SOFI/JBLU/AMKR/GLW/ONDS/QS/RIG 的真实 Yahoo 10 年压力集：
8 个发行人、1045 个不重叠信号、21/63/126 日、SPY 对照、20bp 往返成本。

| 指标 | 21 日 | 63 日 | 126 日 |
|---|---:|---:|---:|
| 技术分-净收益 Spearman | 0.022 | 0.020 | 0.024 |
| 技术分-SPY 超额 Spearman | 0.031 | 0.044 | 0.012 |
| 高分减低分平均净收益 | +0.14% | -2.05% | -4.10% |
| Stage 2 减 Stage 4 平均超额 | -0.11% | +2.35% | +4.48% |

它与上一轮 37 股主研究的弱相关结论一致：技术总分不能证明可稳定提高真实收益，
长期高分组甚至落后。Stage 在 63/126 日仍有风险分层价值，但 21 日为负，仍只应
保留为护栏，不新增买入规则。该 8 股由当日活跃榜事后选取，有选择偏差和幸存者
偏差，不能用于调参。

## 优先级与停止线

1. **高优先**：配置真实 SEC 身份后做少量官方 filing/event shadow；它改善事件
   真实性和生命周期，不等同于收益 alpha。
2. **高优先**：保留 Yahoo 5 日尾部新鲜度补齐；错误交易日输入会直接污染技术过程。
3. **中优先**：持续积累自然到来的公司事件 entity holdout，特别是联合视频、
   并购、供应链和同业标题。
4. **低优先**：CBOE。只有明确要做期权/波动率策略且完成许可时才值得投入；
   对当前股票评分主线不是前置条件。
5. **停止**：不提高动量权重，不改 Stage、P0/P1、估值或交易阈值；不因当前热门股
   压力集表现选择性调参；不以无主体的泛科技标题换 recall。

建议下一轮使用 **GPT-5.6 Sol，high**：配置真实 SEC 身份后，只做官方 filing/event
生命周期 shadow 和 issuer binding；如果仍无真实身份，改用 **GPT-5.6 Terra，
medium** 持续自然 holdout，停止 SEC/CBOE 开发。
