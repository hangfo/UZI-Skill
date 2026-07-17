# 上游择优吸收规范

## 当前基线（2026-07-17）

| 上游 | 本地状态 | 上游状态 | 结论 |
|---|---|---|---|
| `simonlin1212/a-stock-data` | 用户技能 `v3.4.0` | release/HEAD `v3.4.0` (`9ed665c`) | 已更新并用真实端点验证 |
| `simonlin1212/global-stock-data` | 用户技能 `v1.0.1` | release/HEAD `v1.0.1` (`d52a8a0`) | 字节内容一致，无需更新 |
| `wbh604/UZI-Skill` | 正式评分分支包含 `fce996c` | `upstream/main=fce996c` | `ahead 55 / behind 0`，无需合并 |

`upstream` 的 push URL 必须保持 `DISABLED`。不得由本地更新脚本创建或操作原作者 PR。

## 三条吸收通道

### 1. 补充数据技能

`a-stock-data` 和 `global-stock-data` 是按需加载的独立补充层，不是 UZI 生产模块。

1. 只比较不可变 release tag，不直接信任滚动 `main`。
2. 先确认本地文件是否与旧 tag 一致；存在私人修改时做三方语义合并，禁止覆盖。
3. 编译全部 Python fenced blocks。
4. 只对本次新增或修复的端点做小批量真实网络 smoke test，检查字段、排序、日期和空值；不使用 mock 证明线上可用性。
5. 通过后备份旧 `SKILL.md`，再更新用户技能目录。
6. 不因技能新增了同类函数就复制到 UZI。只有真实缓存覆盖审计证明 UZI 存在稳定缺口，且新增 adapter 能提高成功率或权威性，才进入 UZI 隔离分支。

### 2. UZI 主引擎

1. 从已验证正式检查点新建 `codex/*-upstream-<sha>` 隔离分支。
2. 使用 merge 保留上游 ancestry；不在正式评分分支直接试合并。
3. 对重叠文件做语义审查，特别是流程、数据契约、路由、registry 和评分纯函数边界。
4. 使用同一批冻结真实输入做 baseline/candidate 对照；core、holdout、真实 overlay、对抗边界及 lite/medium 必须一致覆盖。
5. 硬门槛包括：零 `possible_regression`、交易决策护栏不松动、缺失值不伪装成精确值、纯评分无性能回退、Windows/Mac 路径兼容。
6. 通过后先推个人 origin 的隔离分支，经独立复核后再 fast-forward 正式分支。绝不推 upstream。

### 3. 观察但不吸收

以下变化默认只记录：README 排版、营销数字、没有真实缺口支撑的新 provider、重复 fallback、依赖升级、扩大重试或并发、不能稳定复现的参数调优。它们不应借“同步上游”进入生产路径。

## 本轮重叠判断

| `a-stock-data v3.4.0` 变化 | UZI 已有能力 | 处理 |
|---|---|---|
| 解禁字段 `FREE_SHARES_TYPE/FREE_SHARES/ABLE_FREE_SHARES` | 资金流维度已消费 `unlock_schedule` | 保留在补充技能；后续若真实 UZI 缓存仍为空，再单独修 adapter |
| 行业榜 `fid=f3` 排序 | UZI 有行业与 peer 数据源 | 保留在补充技能；不改变评分输入排序 |
| 财联社签名电报 | UZI registry/新闻层已有 CLS 入口 | 作为独立真实备源；未证明缺口前不重复接入 |
| 交易所龙虎榜备源 | UZI 已有 akshare、东财、Tushare 与浏览器补源 | 不复制；官方源可作为未来失败率 shadow 候选 |
| 新浪资金流备源 | UZI 已有主力资金流与多源 fallback | 不复制，避免字段口径混用 |
| 深交所/东财公告备源 | UZI 已有巨潮、东财、交易所及结构化事件链 | 不复制，避免公告重复计权 |

## Windows 操作入口

`local-ops/windows/update-uzi.ps1` 现在默认仅审计：它会核对 release、哈希、当前分支和 UZI ahead/behind，但不会 reset、merge、安装依赖或覆盖技能。

只有人工完成 release diff 与真实 smoke test 后，才显式运行：

```powershell
powershell -ExecutionPolicy Bypass -File D:\UZI-Skill\local-ops\windows\update-uzi.ps1 -Mode ApplySkills
```

该模式也只更新两个用户级补充技能；UZI 代码仍必须走隔离分支流程。

## 剩余风险

- release tag 能降低供应链漂移，但不能证明所有端点长期稳定；应记录失败率、字段完整率和响应时间后再考虑生产接入。
- 东财、财联社、交易所接口可能改变反爬或 schema；失败必须显式暴露，不能填默认值。
- `a-stock-data` 是单文件可执行示例集合，函数间共享的 `UA`、限流和 helper 需要按章节加载；不能把孤立代码块误当成可直接 import 的稳定库。
- 本轮真实 smoke test 验证的是正确性与可达性，不等于大批量性能许可；生产并发、缓存 TTL 和 rate limit 必须另行 shadow。
