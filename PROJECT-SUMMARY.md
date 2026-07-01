# UZI-Skill 项目摘要

## 当前定位

UZI-Skill 是本地 Codex-only 股票研究与报告生成项目。当前 Windows 原生安装固定在：

- 项目目录：`D:\UZI-Skill`
- 虚拟环境：`D:\UZI-Skill\.venv`
- 运行 Python：`D:\UZI-Skill\.venv\Scripts\python.exe`
- 用户级 Skills：`%USERPROFILE%\.agents\skills`
- 全局 AGENTS：`%USERPROFILE%\.codex\AGENTS.md`

## 使用方式

常用命令从项目根目录执行：

```powershell
D:\UZI-Skill\.venv\Scripts\python.exe run.py 600519.SH --depth medium --no-browser
D:\UZI-Skill\.venv\Scripts\python.exe run.py MSTR --depth medium --no-browser
```

默认不运行 deep，不设置 `UZI_CLI_ONLY`，不设置 `UZI_PIPELINE`。`MX_APIKEY` 是可选数据源增强，不是基础运行必需项。

## 本地运维文件

机器本地文件统一放在：

```text
D:\UZI-Skill\local-ops\
```

其中：

- `local-ops\windows\update-uzi.ps1`：本地更新脚本。
- `local-ops\windows\uzi-doctor.ps1`：本地诊断脚本。
- `local-ops\windows\UZI-Skill-local-python311-fixes.patch`：Python 3.11 本地兼容补丁。
- `local-ops\windows\uzi-skill-update-state.json`：最近一次本地更新状态。
- `local-ops\artifacts\`：临时图表、脚本等本地试验产物。

`local-ops/` 和 `.venv/` 已加入 `.git/info/exclude`，不会出现在提交列表中。

## Git 与 Python

推荐使用系统 Git：

```text
C:\Program Files\Git\cmd\git.exe
```

`D:\MinGit` 仅作为安装阶段留下的备用便携 Git，不再放在用户 PATH 中。

Python 环境：

- 系统中存在 Python 3.14 和 Python 3.11。
- UZI-Skill 固定使用项目 venv：Python 3.11.9。
- `.venv/` 是项目运行环境，不提交到 GitHub。

## 已验证报告

以下 medium 验证已成功：

- `600519.SH`
- `MSTR`

报告输出目录：

```text
D:\UZI-Skill\skills\deep-analysis\scripts\reports\
```

该目录已被项目 `.gitignore` 忽略。

## 本地补丁说明

当前保留两个 Python 3.11 兼容补丁文件：

- `skills/deep-analysis/scripts/lib/report/institutional.py`
- `skills/deep-analysis/scripts/lib/report/segmental.py`

补丁目的：修复 Python 3.11 对嵌套 f-string 中反斜杠表达式的语法限制。对应 patch 已保存在 `local-ops\windows\UZI-Skill-local-python311-fixes.patch`，更新脚本 reset 后会自动尝试重新应用。

## 上游与本地同步

本机同时跟踪两个远程：

- `origin`：Windows 本机当前默认远程。
- `hangfo`：MacBook 开发仓库 `https://github.com/hangfo/UZI-Skill.git`。

截至 2026-07-01，`hangfo/main` 与本机基线提交一致。已合入 `hangfo/codex/local-mac-stable` 的可移植修复：

- 市场数据单位归一化，避免市值、涨跌幅、YTD 等字段被旧缓存或不同源单位放大。
- lite 深度 fetcher 范围修正。
- 美股/港股/A 股基础数据与 K 线兜底增强。
- 买入评分与传统总评分离，避免把投机性高涨幅误判成综合高分。
- `--no-open-report` CLI 参数，便于 Windows / macOS / 自动化环境生成报告但不弹浏览器。
- Python 3.11 报告渲染兼容修复。

未合入 `hangfo/hermes-compat`，因为该分支包含大规模删除和结构瘦身，适合单独评审，不适合作为正式试用前的稳定合并。

## MacBook 本地包导入

2026-07-01 已校验并隔离导入 MacBook 本地备份包：

```text
D:\工作\uzi-local-state-tools-20260701-041104-v2.tgz
```

校验 SHA256：

```text
8CBDBD25877FF12AFF7880F7640E096A571B5914B9FC71B233937F830FF7D285
```

导入原则：

- Bash 更新/同步脚本只作为 Mac 历史参考，不进入 Windows 执行路径。
- `enhanced_medium.py` 作为本地实验工具保留在 `local-ops\tools\`，并改为自动识别 Windows/macOS 仓库根目录。
- Mac 验证记录和 evidence cache 保存在 `local-ops\state\`。
- 这些本地工具和状态仍由 `.git/info/exclude` 排除，不提交到 GitHub。

Windows 本地入口：

```powershell
powershell -ExecutionPolicy Bypass -File D:\UZI-Skill\local-ops\tools\run-enhanced-medium.ps1 AXTI -NoStage2
```

## 提交前检查

提交 GitHub 前建议运行：

```powershell
git status --short
D:\UZI-Skill\.venv\Scripts\python.exe -m py_compile D:\UZI-Skill\skills\deep-analysis\scripts\lib\report\institutional.py
D:\UZI-Skill\.venv\Scripts\python.exe -m py_compile D:\UZI-Skill\skills\deep-analysis\scripts\lib\report\segmental.py
D:\UZI-Skill\.venv\Scripts\python.exe -m pytest D:\UZI-Skill\skills\deep-analysis\scripts\tests\test_market_unit_normalization.py D:\UZI-Skill\skills\deep-analysis\scripts\tests\test_us_market_data_validation.py D:\UZI-Skill\skills\deep-analysis\scripts\tests\test_investment_score_calibration.py -q
```

预期 Git 状态只包含要提交的源码/文档改动，不包含 `.venv/`、报告、缓存或 `local-ops/`。
