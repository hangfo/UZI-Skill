# 三上游吸收审计（2026-08-25）

## 结论

- `a-stock-data`：正式版与 HEAD 均为 `v3.7.1` / `f90d67853b8108f13d286e1df20b357e2c5198a9`。已把用户级技能从 `3.5.1+uzi.1` 升到 `3.7.1+uzi.1`，保留东财按首屏实得长度翻页的本机补丁。
- `global-stock-data`：正式版与 HEAD 均为 `v2.0.3` / `c0b3ed8d8a1fdff0932e5899fc64a5994308a5ef`。本机规范化内容逐字一致，不做无意义覆盖。
- `UZI-Skill`：GitHub 最新正式 release 仍是 `v3.9.1`（tag `337d50255eb7166eb95d322d1e7440b0344e0653`）；`main` HEAD 是未发布演进 `b004d7a988ca53a4805bf36784af091fa1209f22`。在 `codex/upstream-intake-20260825` 语义合并，保留本地证据治理与显式 FCF/净债务契约。

## 采纳与舍弃

采纳：A 股 920 迁移与后缀路由、调整因子/筹码/估值史/宏观端点；UZI 全球同行、US TTM、负 ROE 保留、负 PE 不翻正、缺失数据不造中性值、真实资产负债表、进程硬超时、报告空值与移动端修复。

保留本地：SEC 真实身份 fail-closed、FRED evidence-only、Massive 非改写 EOD shadow、Yahoo 只追加严格更新日期、SEC Item 4.01 正文语境、显式 FCFF 与同期间净债桥、动态评分极化。未采纳任何评分、动量、Stage、P0/P1、估值或交易阈值调参；未接 TradingView 非官方接口；CBOE 请求为零。

## 验证

- UZI 新增/相关 direct-compatible：`56/56`；全部变更 Python 编译与 `git diff --check` 通过。
- 同输入 branch harness 双向：各 `117/117 ok`，`0 review`，`0 possible_regression`，评分与档位零意外变化。
- A 股技能：`58/58` Python fence；真实 920002、688146、601127、上证指数、平安银行报价；东财行业总数 496，成功返回前 205，证明动态分页补丁仍必要。
- 全球技能：`35/35` Python fence；真实 AAPL、00700.HK、FINRA、Treasury、CFTC；SEC 未声明身份 fail-closed；CBOE network called=false。
- 真实 UZI NVDA lite：当前行情重新采集，综合 `57.1/100`、观望中性、critical=0。首次运行发现缺失护城河证据在机构 idea screen 的 `None >= 28`，已修复并用同一真实缓存复验 dim 20/21/22 全部成功。

## 持续吸收规则

1. 固定上游 commit 与 release tag，先区分正式 release 和未发布 HEAD。
2. 每个上游使用独立 intake 分支；按“数据真实性、实体路由、证据治理、评分消费”分层审查重叠。
3. 对共享文件做三方语义合并，不整份选择一侧；本地安全/缺失值契约优先。
4. 先跑新增回归，再跑真实端点、双向同输入评分和生产报告；只有零 secret、零 possible regression、零意外档位变化才允许快进正式分支。
5. 外部技能保留 immutable 原版和本地补丁清单；无差异不升级，新增依赖不自动安装。

证据快照：`local-ops/vendor-audit/20260825/stock-skill-smoke.json`。
