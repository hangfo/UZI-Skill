# SEC/FRED/Massive secure shadow 独立正式吸收审计（2026-07-30）

## 结论

候选 `codex/scoring-validation-sec-fred-massive-shadow@667f54322ecdd286c646994a672ca08b7b87efa6`
满足正式吸收硬门槛，已用 `--ff-only` 吸收到
`codex/scoring-validation-guardrails`。这是证据质量与凭据治理改进，不是收益增强结论：

- 正反同输入比较在新增真实缓存后均为 `113 ok / 0 review / 0 possible_regression`；
  综合分、投资分、Stage 和交易档位均无意外变化。
- 仓库历史与候选提交的通用敏感信息扫描、已配置真实值逐提交精确扫描均为 0 命中；
  DPAPI CurrentUser 创建、读取、空值保留、更新、环境覆盖、篡改 fail-closed 与临时明文清理均通过。
- SEC、FRED、Massive 脱敏实时端点复验通过；CBOE 0 请求，未接入 TradingView
  非官方接口。
- 候选相对正式分支为纯 fast-forward；没有评分、动量、P0/P1、估值或交易阈值代码重叠。
- Massive 继续只做 EOD shadow，`overwrote_primary=false`；FRED 继续只保留原始观察值；
  SEC Item 4.01 继续按正文语境 shadow，不能仅凭 item code 自动归类负面。

## 分支与权限边界

| 项目 | 审计值 |
|---|---|
| 正式吸收前 | `codex/scoring-validation-guardrails@fff93f6388ed605c7cf56ad4cad7133eb7681018` |
| 候选检查点 | `codex/scoring-validation-sec-fred-massive-shadow@667f54322ecdd286c646994a672ca08b7b87efa6` |
| 拓扑 | `fff93f6..667f543`，5 commits，纯 fast-forward |
| `upstream/main` | `fce996c33e70eddce8e375f53cd252b549eb3d7c`，未修改 |
| `main` | `fce996c33e70eddce8e375f53cd252b549eb3d7c`，未修改 |
| `codex/windows-local-stable` | `7115a7019d4295889ed816057084d33207f640d5`，未修改 |
| upstream push URL | `DISABLED` |
| 推送范围 | 只允许个人 `origin/codex/scoring-validation-guardrails`；不创建 PR |

## 安全与生命周期复验

1. 通用 secret pattern 扫描为 0 命中。
2. 从仓库外 DPAPI 存储读取已配置键，只在内存中对候选及其 5 个提交的 Git
   archive 做精确字节匹配：`secret_match_count=0`；未输出真实值。
3. 加密文件位于仓库外。DPAPI 生命周期检查全部通过：
   `created/plaintext_absent/roundtrip/blank_preserves/update_adds/environment_wins/tamper_fails_closed=true`。
4. `tools/validate_secure_sources.py --network --json` 脱敏结果：
   SEC live 可用；FRED 返回最新观察；Massive 返回 8 根 EOD bars。
5. 未访问 CBOE；未使用 TradingView cookie、私有端点或非官方行情接口。

## 同输入分支 harness

比较包含 core、holdout、自动发现真实缓存、冻结 evidence overlays、7 个 synthetic
对抗样本，并同时运行 lite/medium。

| 方向 | raw + synthetic | ok | review | possible regression |
|---|---:|---:|---:|---:|
| 正式 `fff93f6` → 候选 `667f543` | 106 + 7 | 113 | 0 | 0 |
| 候选 `667f543` → 正式 `fff93f6` | 106 + 7 | 113 | 0 | 0 |

所有同输入评分和交易档位 delta 为 0。候选不修改 `score_fns.py`，也不修改动量、
Stage、P0/P1、估值或交易阈值。

## 真实热门/动量股生产复验

样本在查看 UZI 结果前，从 2026-07-29 Yahoo most-active/day-gainers/day-losers
冻结，避免按评分挑样本。上涨样本为 LAD、EXLS、CBZ、GEHC；VRT、HIMS 是大跌
对照。全部使用真实生产入口、真实最新数据，未用 mock。

| ticker | depth | overall | investment | Stage | RSI | 交易结论 |
|---|---|---:|---:|---:|---:|---|
| LAD | lite | 41.2 | 56.0 | 3 | 87.18 | avoid |
| EXLS | medium | 44.8 | 59.0 | 3 | 77.76 | avoid |
| CBZ | lite | 46.0 | 56.0 | 3 | 86.51 | avoid |
| GEHC | medium | 43.0 | 59.0 | 4 | 63.99 | avoid |
| VRT | medium | 46.8 | 60.8 | 1 | 13.58 | quality_watch，等待趋势/催化确认 |
| HIMS | lite | 42.7 | 38.7 | 4 | 26.79 | avoid |

六股均 `critical=0`。Massive 对六股的 2026-07-29 收盘 shadow 与 Yahoo 日期一致、
close 基本一致，且全部 `overwrote_primary=false`。这与稍早一次免费层落后一交易日
的观测共同说明延迟并不稳定，因此它只能承担 EOD 交叉核验，不能替换 Yahoo 主行情。
medium 样本的 FRED 8 个 series 为 ready，但不生成情绪或评分解释；lite 未抓宏观是
深度设计，不是缺陷。

## 真实历史收益验证与上次比较

方法：Yahoo 10 年复权日线、SPY 同期基准、信号收盘后下一收盘入场、21/63/126
交易日、不重叠 issuer 窗口、20bp 往返成本。新六股共 750 个信号，无抓取失败。

| 样本 | 指标 | 21d | 63d | 126d |
|---|---|---:|---:|---:|
| 新六股 | 技术分-超额 Spearman | +0.0049 | -0.0521 | -0.1252 |
| 新六股 | 高分减低分平均超额 | -1.50% | -5.47% | -10.49% |
| 上次六热门股 | 技术分-超额 Spearman | -0.021 | -0.036 | -0.000 |
| 上次六热门股 | 高分减低分平均超额 | -1.10% | -4.40% | -16.17% |
| 37 股主样本 | 技术分-超额 Spearman | +0.025 | +0.042 | +0.058 |
| 37 股主样本 | 高分减低分平均超额 | +0.77% | +2.52% | -5.08% |

新样本方向偏负，和上次热门股压力集一致，但不能据此把指标反向做空：两批样本都小、
按当前热门榜形成且有幸存者偏差。公允结论仍是技术分没有稳定单调 alpha；现有 Stage
最多保留为风险护栏，不提高动量权重，也不反向调参。

冻结产物：

- `local-ops/state/us-momentum-backtest/20260730-independent-six-holdout-prices.json`
- `local-ops/state/us-momentum-backtest/20260730-independent-six-holdout-final.json`
- `local-ops/state/us-momentum-backtest/20260730-independent-six-holdout-final.md`

## SEC Item 4.01 正文语境复核

除 IREN 外，又从 SEC 官方全文检索中检查多个独立发行人的 Item 4.01 正文。BZYR
明确无分歧/无 reportable events；GRPS 说明审计师变更并非分歧导致且无 adverse
或 disclaimer；BGFR 同样无分歧，但旧审计报告包含 going-concern explanatory
paragraph。另两个 amendment 正文没有足够上下文，未作归类。

这些独立样本证明同一 item code 的实质语境不同，既不能自动负面，也不能自动正面。
因此：

- 保留全文语境 shadow 和 `score_consumption_allowed=false`；
- 没有清晰发行人绑定、正文证据、时效和解决态时 fail closed；
- 不改现有事件映射、评分消费或阈值；
- 当前样本已足够否定 item-code-only 规则，停止为调参继续扩源。

## 测试与已知非候选失败

- SEC/FRED/Massive、overlay、wire、branch harness 相关 direct tests：`92/92`。
- 可由 direct runner 执行的其余 49 个测试文件：`615/618`。3 个失败均可在正式
  基线复现且与候选无重叠：旧 Tencent 市值 fallback 断言、POSIX executable bit
  在 Windows 的检查、Windows drive path 交给 bash 的语法检查。
- 13 个显式依赖 pytest 的文件在当前无 pytest 的既定环境下未运行；未安装依赖。
- 所有候选 Python 文件 `py_compile` 通过，`git diff --check` 通过。

## 投资与开发停线

本轮提高的是“来源真实性、凭据安全、跨源日期可见性”，没有证明收益提升。VRT 的
`quality_watch` 只是“基本质量尚可但技术超卖后等待确认”，不是抄底指令；其余五股
当前均没有足够证据升级档位。

下一步只积累自然时间形成的新 holdout，并优先建立可复现、包含退市证券的
point-in-time 美股宇宙。拿不到这种数据就停止动量优化。不得用当前小样本调评分、
动量、Stage、P0/P1、估值或交易阈值。
