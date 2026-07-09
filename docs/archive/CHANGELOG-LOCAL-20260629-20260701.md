# 本地变更日志

本文件记录本机 UZI-Skill 安装、修复、验证和清理动作，便于后续提交 GitHub 前追溯。

## 2026-07-01

### Self-review 误报修复

- 修复 `self_review.check_factcheck_redflags` 将 `AAPL / Apple Inc.` 公司名误判为“苹果产业链”声称的问题。
- 同步处理 `TSLA / Tesla` 同类边界：公司自身名称不触发供应链红旗。
- 保留对抗性检查：非 Apple / Tesla 公司如声称 Apple / Tesla 供应链，但主营没有光学、镜头、代工、电池、零部件等支撑词，仍会触发 warning。
- 新增 `test_self_review_factcheck_redflags.py`，覆盖：
  - Apple 本体不误报；
  - 非 Apple 供应链声称仍拦截；
  - 有光学/精密主营证据时放行；
  - Tesla 本体不误报。

### Lite / Medium 回归

- AAPL lite / medium 复验：原“苹果产业链”误报 warning 已收敛，只剩 CLI/lite 可接受的 `agent_analysis.json` 缺失 warning。
- 同篮子 lite 复验成功：`600519.SH`、`AAPL`、`AXTI`、`00700.HK`。
- 同篮子 medium 复验成功：`600519.SH`、`AAPL`、`AXTI`、`00700.HK`。
- 观察到 A 股 `600519.SH` medium 会触发 859 项持仓/基金类枚举，约 7 分钟完成；这是性能优化候选，不是功能失败。

### GitHub / Gmail 对比

- 添加并读取 MacBook 开发远程 `hangfo`：`https://github.com/hangfo/UZI-Skill.git`。
- 确认 `hangfo/main` 与本机当前基线提交一致。
- 对比 `hangfo/codex/local-mac-stable`、`hangfo/codex/mac-python311-no-open-report`、`hangfo/hermes-compat`。
- Gmail 本地化邮件正文记录了本地工具/状态备份包 v2、AXTI YTD 交叉验证、以及 Mac 稳定分支修复提交；`.tgz` 附件因 Gmail 连接器不支持 `application/x-tar` 未能直接读取。

### 合入 Mac 稳定分支

- 合入 `hangfo/codex/local-mac-stable` 的 6 个提交内容，但不创建本地提交。
- 合入范围：
  - `run.py` 新增 `--no-open-report`。
  - `fetch_kline.py`、`data_sources.py` 等市场数据单位归一化与兜底增强。
  - `analysis_profile.py`、`collect.py` 修正 lite/no-resume fetcher 口径。
  - `score_fns.py` 新增跨市场买入评分，并保持传统总评与买入评分分离。
  - 新增市场单位、美股数据、投资评分校准测试。
  - 保留并统一 Python 3.11 报告渲染补丁。
- 未合入 `hangfo/hermes-compat`，因为该分支删除范围过大，需要单独评审。

### 备份与冲突处理

- 合并前将本机差异和 Mac 稳定分支补丁保存到 `local-ops\backups\`。
- 两个 Python 3.11 报告文件只发生重复补丁冲突，已统一为预先生成 HTML 片段的写法。
- Windows 原生验证发现 GBK 控制台遇到状态输出特殊符号会抛 `UnicodeEncodeError`，已在 pipeline 输出模块中设置 stdout/stderr 编码容错，不影响 UTF-8 终端。

### 验证

- `py_compile` 通过：合入的 9 个 Python 源码文件均可编译。
- 当前 venv 未安装 `pytest`，未额外安装依赖；使用轻量临时测试执行器跑完 3 个新增测试文件中的 17 个测试函数，全部通过。
- 真实 lite 验证：`AXTI --depth lite --no-browser --no-open-report` 成功生成报告。
  - 报告路径：`D:\UZI-Skill\skills\deep-analysis\scripts\reports\AXTI_20260701\full-report-standalone.html`
  - 综合评分：43.3。
  - 买入评分：37.2。
  - YTD：+330.1%，符合 Gmail 本地化记录中 fresh UZI / yfinance 的约 330% 口径。
  - self-review：critical=0，warning=1；warning 为 lite/CLI 模式可接受的 `agent_analysis.json` 缺失。

### MacBook 本地备份包导入

- 校验并导入 `D:\工作\uzi-local-state-tools-20260701-041104-v2.tgz`。
- SHA256 与 Gmail 正文一致：`8CBDBD25877FF12AFF7880F7640E096A571B5914B9FC71B233937F830FF7D285`。
- 压缩包路径安全检查通过：未发现绝对路径、盘符路径、反斜杠逃逸或 `..` 路径穿越。
- 原始包隔离解压到 `local-ops\imports\macbook-local-state-tools-20260701-v2\`。
- 将 Mac 验证记录归档到 `local-ops\state\macbook-validation-20260701-v2\`。
- 将 enhanced-medium evidence cache 复制到 `local-ops\state\enhanced-medium\`。
- 将 `enhanced_medium.py` 复制到 `local-ops\tools\`，并改造为 Windows/macOS 仓库根目录自定位。
- 新增 Windows PowerShell 包装入口：`local-ops\tools\run-enhanced-medium.ps1`。
- 未迁入 Bash 更新脚本、Bash skill 同步脚本和 Mac 专属路径；这些只作为归档参考。

## 2026-06-30

### 清理与归档

- 将 D 盘根目录的 UZI 运维文件移动到 `D:\UZI-Skill\local-ops\windows\`：
  - `update-uzi.ps1`
  - `uzi-doctor.ps1`
  - `UZI-Skill-local-python311-fixes.patch`
  - `uzi-skill-update-state.json`
- 将临时图表产物移动到 `D:\UZI-Skill\local-ops\artifacts\`：
  - `120d_asset_return_chart.png`
  - `make_120d_asset_return_chart.py`
- 删除安装阶段备份目录 `D:\UZI-Skill-backup-20260629_164918`。
- 将 `.venv/` 与 `local-ops/` 加入本地 `.git\info\exclude`，不修改项目 `.gitignore`。

### Git 与 Python 整理

- 确认系统 Git 已安装：`C:\Program Files\Git\cmd\git.exe`。
- 从用户 PATH 移除 `D:\MinGit\cmd`，保留 `D:\MinGit` 作为备用，不删除。
- 确认 UZI-Skill 固定使用 `D:\UZI-Skill\.venv\Scripts\python.exe`，版本为 Python 3.11.9。
- 保留系统内其他 Python 版本，不删除、不重装。

### 文档

- 新增 `PROJECT-SUMMARY.md`，记录项目路径、运行方式、本地运维文件、Git/Python 策略和提交前检查。
- 新增 `CHANGELOG-LOCAL.md`，记录本地安装和清理过程。

## 2026-06-29

### 安装与验证

- 按 Windows 原生 Codex-only 流程安装 UZI-Skill 到 `D:\UZI-Skill`。
- 创建并使用 `D:\UZI-Skill\.venv`。
- 安装数据 Skills 到 `%USERPROFILE%\.agents\skills`：
  - `a-stock-data`
  - `global-stock-data`
- 写入全局 AGENTS：`%USERPROFILE%\.codex\AGENTS.md`。
- 创建本地更新脚本与诊断脚本。

### Python 3.11 本地补丁

- 修复 `institutional.py` 中 Python 3.11 不兼容的嵌套 f-string 反斜杠表达式。
- 修复 `segmental.py` 中同类 Python 3.11 f-string 语法问题。
- 保存补丁为 `UZI-Skill-local-python311-fixes.patch`。
- 更新脚本在 `git reset --hard origin/main` 后会自动尝试重新应用该补丁；如果无法应用，会提示可能上游已修复而不中断。

### Medium 验证

- `600519.SH --depth medium --no-browser` 成功。
- `MSTR --depth medium --no-browser` 成功。
- 已确认报告 HTML、share-card 和 war-report 均可生成。

### 明确未做事项

- 未安装 TradingAgents-Astock。
- 未安装额外独立多 Agent 框架。
- 未设置 `CODEX_HOME`。
- 未永久设置 `UZI_CLI_ONLY`。
- 未设置 `UZI_PIPELINE`。
- 未配置 `MX_APIKEY`。
- 未删除或重装 Git/Python。
