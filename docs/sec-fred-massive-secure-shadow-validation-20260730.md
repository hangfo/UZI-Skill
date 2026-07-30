# SEC / FRED / Massive 安全接入与真实美股 shadow 验证（2026-07-30）

## 公允结论

本轮值得保留的是“安全配置 + 官方证据 shadow”，不值得做的是把新数据源直接变成
评分或交易信号。

- SEC：高优先，继续沿用显式联网与真实联系身份门禁。官方 filing/event 只先进入
  冻结 overlay，不直接改分。
- FRED：值得加入，但只保存原始观察值、观察日期和 realtime/vintage 日期，不把
  利率、期限利差、信用利差或 VIX 自动翻译成利好/利空。
- Massive Stocks Basic：只作为独立 EOD 日线新鲜度/收盘价对照。免费层不是实时源，
  split-adjusted 也不等于 dividend-adjusted，因此不得覆盖 Yahoo/yfinance 主序列，
  不得拼入总回报回测。
- TradingView Premium：不接行情。Premium 是网站订阅，不等于可供 UZI 调用的通用
  数据 API；Advanced Charts 的 Datafeed API 仍要求使用者自备数据。以后若确有用户
  自建 alert，可单独评估 webhook 入站，不能把登录 cookie 或非官方库做生产源。
- CBOE：继续零联网。当前主线是股票评分和公司事件，不是期权链、IV 或 0DTE；没有
  明确产品问题和许可前，收益/合规比不足。

## 安全配置

新增 `configure-data-sources.cmd` 与原生 Windows 遮罩窗口。值只写入
`%LOCALAPPDATA%\UZI-Skill\secure-sources.v1.json`，由 Windows DPAPI
CurrentUser 加密，仓库、`.env`、命令行参数、终端输出和报告均不保存明文。
显式进程环境变量优先于加密配置。必须说明的边界是：UZI 发请求时仍需在当前进程
内存中短暂解密；DPAPI 防止仓库泄漏和静态明文泄漏，不防当前 Windows 账户已经被
完全控制。

SEC 输入应为真实 `姓名或机构 + 可监控联系邮箱`，不是 SEC API Key。空白字段保留
既有值。验证器只输出 `ok/unavailable`、行数和脱敏错误，不输出凭据。

用户已在遮罩窗口本机输入三项值。独立脱敏复验结果：

- SEC：配置门禁通过，`company_tickers.json` 真实请求通过；
- FRED：配置门禁通过，DFF 真实请求返回 2 条观察；
- Massive：配置门禁通过，AAPL 真实请求返回 7 根 EOD bar；
- 输出、仓库 diff、报告和冻结数据均没有凭据。

## 官方源真实 shadow

### FRED

8 项 snapshot 全部 `ready`、0 error：

| 序列 | 最新观察日 | 值 | realtime/vintage 日 |
|---|---|---:|---|
| DFF | 2026-07-28 | 3.63 | 2026-07-29 |
| DGS2 | 2026-07-28 | 4.26 | 2026-07-29 |
| DGS10 | 2026-07-28 | 4.61 | 2026-07-29 |
| T10Y2Y | 2026-07-29 | 0.45 | 2026-07-29 |
| BAMLH0A0HYM2 | 2026-07-28 | 2.84 | 2026-07-29 |
| VIXCLS | 2026-07-28 | 18.21 | 2026-07-29 |
| CPIAUCSL | 2026-06-01 | 332.568 | 2026-07-14 |
| UNRATE | 2026-06-01 | 4.2 | 2026-07-26 |

这些值只说明公开宏观状态。期限利差为正、信用利差/VIX 的绝对水平都不能在没有
历史分位和 point-in-time 研究时自动等于买入信号。完整公开数据：
`local-ops/state/official-source-shadow/20260730-fred-snapshot.json`。

### Massive

PATH/IREN/HURN/GRMN/MANH/AVTR 的 Yahoo 主序列都到 2026-07-29，Massive Basic
都只到 2026-07-28，状态统一为 `massive_delayed_or_market_open`，且
`overwrote_primary=false`。这是真实证据证明免费层不适合实时决策。

真实运行还发现原实现会对不同日期计算 close 差，可能把 HURN/MANH 的事件跳涨
误呈现为同日源冲突。最小修复改为：只有同日才计算 `close_diff_pct`；异日只输出
`calendar_gap_days=1`。这提高证据精度，不触碰行情、指标或评分。

完整公开结果：
`local-ops/state/official-source-shadow/20260730-massive-eod-compare.json`。

### SEC lifecycle

| 股票/目标 | 结果 | 官方事实与公允标签 |
|---|---|---|
| HURN negative_event | gap | SEC submissions、诉讼与停牌源均无合格 P0/P1；不推断负面 |
| IREN negative_event | metadata ready，但结论 ambiguous | 2025-11-28 8-K Item 4.01；精确 CIK/ticker 绑定 |
| GRMN missing_financials | ready | SEC companyfacts CIK0001121788 可补财务证据 |

IREN 不能机械当作 active P1：8-K 正文写明审计师变更，但无审计分歧、无否定或拒绝
表示意见；其中提及的 2024 内控重大缺陷，2025-06-30 10-K 已明确声明整改完成并经
测试有效。因此本轮不把该 overlay 喂给评分，也不因一个样本立刻修改全局 4.01
映射。停止线是先积累更多 4.01 官方正文；若“无分歧 + 已整改”稳定出现，再开发
正文语义分层，而不是只靠 item code。

冻结文件：

- `local-ops/state/official-source-shadow/sec-lifecycle/HURN-negative_event.json`
- `local-ops/state/official-source-shadow/sec-lifecycle/IREN-negative_event.json`
- `local-ops/state/official-source-shadow/sec-lifecycle/GRMN-missing_financials.json`
- `local-ops/state/official-source-shadow/20260730-sec-lifecycle-context-review.json`

## 实现边界

- `lib/fred_source.py`：`DFF/DGS2/DGS10/T10Y2Y/BAMLH0A0HYM2/VIXCLS/
  CPIAUCSL/UNRATE`，只读官方观察值；历史研究必须保留 realtime/vintage 日期。
- `fetch_macro.py`：仅 US/G 路由附加 `official_macro_observations`；原
  `rate_cycle/fx_trend/fallback` 语义不变，评分层不读取新字段。
- `lib/massive_source.py`：Bearer 鉴权、每股有界日聚合、纽约交易日转换；只报告
  `match/primary_stale/massive_delayed_or_market_open/same_date_close_conflict/gap`。
- `fetch_kline.py`：只附加 `massive_eod_shadow`，不修改 klines、指标或评分输入。
- `evidence_overlay_builder.py`：CLI 可读取同一 DPAPI SEC 身份；显式环境变量仍优先，
  身份门禁和限速保持不变。
- CBOE 请求与生产路由均为 0。

## 当日真实样本与选择理由

Yahoo `most_actives` 与 `day_gainers` 在 2026-07-30 运行时返回的最近完整交易日为
2026-07-29。样本在查看 UZI 结果前按不同难度冻结：

| 股票 | 选择理由 | 深度 | 综合 / 买入分 | 技术状态 | 交易结论 |
|---|---|---|---:|---|---|
| PATH | 活跃榜；成熟软件但长期结构受损 | lite | 48.4 / 59.0 | Stage 4；距年高 -34.7% | 回避或仅跟踪 |
| IREN | 活跃榜；高波动算力/数据中心主题 | medium | 45.7 / 54.0 | 低于 MA20/MA200；距高 -61.6% | 回避或仅跟踪 |
| HURN | 当日约 +40% 的事件型跳涨 | lite | 45.1 / 56.0 | Stage 3；RSI 87.1 | 回避或仅跟踪 |
| GRMN | 当日约 +16% 的成熟质量股 | medium | 52.3 / 70.1 | Stage 2；RSI 78.5 | 质量观察池，等待确认 |
| MANH | 当日约 +21%；软件质量/估值对照 | medium | 45.8 / 56.0 | Stage 3；RSI 76.0 | 回避或仅跟踪 |
| AVTR | 当日约 +15.8%；低质量反弹对照 | lite | 40.4 / 38.0 | Stage 3；RSI 84.7 | 回避 |

六份生产报告均 `critical=0`。PATH/IREN/HURN/MANH/AVTR 说明“活跃、大跌反弹或单日跳涨”
不会自动升级买入；GRMN 质量、成长和趋势更好，但估值/催化/共识不足，仍没有被
追涨逻辑推成买入。

评分过程也有必须保留的限制：四股的 US 宏观/行业/材料等若干维度仍有真实数据
缺口，CLI 报告没有 agent role-play；因此综合分适合做相对风险筛选，不应被解释为
精确目标收益。GRMN 的质量轴 `94.0`、成长轴 `73.8`，但估值轴 `52.0`、催化轴
`50.0`，买入分与低 panel 共识出现明显分歧；合理动作是进入观察池核验财报后的
盈利持续性和估值，而不是因为 70.1 分追涨。HURN 的单日 gap 会把趋势和 RSI
同时抬高，Stage 3/RSI 护栏避免把一次事件冲击误当成稳定趋势，但也不能据此机械
做空。

报告：

- `skills/deep-analysis/scripts/reports/PATH_20260730/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/IREN_20260730/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/HURN_20260730/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/GRMN_20260730/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/MANH_20260730/full-report-standalone.html`
- `skills/deep-analysis/scripts/reports/AVTR_20260730/full-report-standalone.html`

## 历史收益检验与上轮比较

六股用真实 Yahoo 10 年复权日线、SPY、下一收盘入场、21/63/126 日不重叠窗口和
20bp 往返摩擦，共 724 个信号。它是当前热门/跳涨股压力样本，有选择偏差和
幸存者偏差，只能做反证压力测试。

| 指标 | 21 日 | 63 日 | 126 日 |
|---|---:|---:|---:|
| 技术分-净收益 Spearman | -0.018 | -0.051 | -0.006 |
| 技术分-SPY 超额 Spearman | -0.021 | -0.036 | -0.000 |
| 高分减低分平均超额 | -1.10% | -4.40% | -16.17% |
| Stage 2 减 Stage 4 平均超额 | -2.04% | -4.01% | -15.78% |

上轮 37 股主样本技术分-超额 Spearman 为 `+0.025/+0.042/+0.058`，高低分平均
超额为 `+0.77/+2.52/-5.08%`；其结论已经是不支持提高动量权重。再上一轮
INTC/SOFI/JBLU/AMKR/GLW/ONDS/QS/RIG 压力集为
`+0.031/+0.044/+0.012`，高低分平均净收益为 `+0.14/-2.05/-4.10%`。
本轮方向更差，且 Stage 4 的超额主要由强反弹和小样本构成。公允结论不是反向做空，
而是技术总分和 Stage 都不具备稳定、单调、跨样本的独立 alpha；Stage 继续只做
风险护栏。

冻结价格与完整结果：

- `local-ops/state/us-momentum-backtest/20260730-sec-fred-massive-six-hot-prices.json`
- `local-ops/state/us-momentum-backtest/20260730-sec-fred-massive-six-hot-final.json`
- `local-ops/state/us-momentum-backtest/20260730-sec-fred-massive-six-hot-final.md`

## 回归、对抗性与性能

- 相关 direct tests：`230/230` 通过。
- 全目录 direct 试跑：`614/617`；3 项为既有且与候选无关的问题——旧市值 fallback
  断言、Windows 无 POSIX 可执行位、Windows bash 语法检查超时。另有 pytest-only
  文件因项目 venv 未安装 pytest 未运行；本轮没有安装依赖。
- baseline=`3b8637a`，candidate tree=`e8016244`：
  `96 raw + 7 synthetic = 103`，正反顺序均 `103 ok / 0 review /
  0 possible_regression`，所有 overall/buy/fundamental/panel 分数和档位变化为 0。
- 正向进程 `11.733s -> 7.611s`；交换顺序为候选 `9.516s`、正式基线
  `9.170s`。两轮均无
  performance warning。纯评分调用栈未改，只判“无性能回退”，不宣称提速。
- active P0/P1、伪造、已解决、过期、cross-issuer、MU/Musk、常见词 ticker 和
  substring 边界继续由同一冻结 harness 与专项 tests 覆盖。
- `py_compile`、`git diff --check` 与 progress JSONL 校验通过。

最终对照：

- `local-ops/state/branch-score-compare/20260730-sec-fred-massive-shadow-final.md`
- `local-ops/state/branch-score-compare/20260730-sec-fred-massive-shadow-final-swap.md`

## 停止线与是否值得吸收

三项真实凭据与端点均已通过，FRED/Massive 在真实生产缓存中可见；不同日价差误导
也由真实样本发现并修复。代码方向具备净证据收益。满足最终测试和冻结门禁后，建议
提交并只推送隔离分支；不自动合回正式分支：

1. FRED 不自动生成宏观利好/利空，不参与历史回测，避免修订数据穿越。
2. Massive 不当实时源，不覆盖 Yahoo，不因免费层限速失败而阻断生产。
3. TradingView 不抓 cookie、不用非官方行情 API；除非有明确 webhook alert 产品。
4. CBOE 无许可、无明确期权问题时零请求。
5. 不调评分、动量、Stage、P0/P1、估值和交易阈值。
6. 不用当前热门样本选择性调参；若拿不到 point-in-time 且含退市股的无幸存者偏差
   宇宙，停止动量优化。

下一步不再扩数据源。若要继续 SEC 4.01 正文语义/lifecycle，使用
**GPT-5.6 Sol / high**；若只做独立复核、例行数据新鲜度和 upstream intake，
使用 **GPT-5.6 Terra / medium**。
