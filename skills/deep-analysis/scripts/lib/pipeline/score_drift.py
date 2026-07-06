"""score_drift.py — 巧思：评分漂移追踪器

每次运行完成后把三轨分数追加到 .cache/_global/score_history.jsonl，
并提供 report() 函数打印历史对比，帮助识别因代码/权重/数据变化引起的评分漂移。

用法（run.py 调用）:
    from lib.pipeline.score_drift import record, report
    record(ticker, result)             # 追加记录
    report(ticker)                     # 打印漂移表
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


# ── 存储路径 ──────────────────────────────────────────────────────────────────
def _history_path() -> Path:
    """返回全局历史文件路径，自动创建父目录。"""
    base = Path(os.environ.get("UZI_CACHE_DIR", ".cache"))
    d = base / "_global"
    d.mkdir(parents=True, exist_ok=True)
    return d / "score_history.jsonl"


# ── 写入 ──────────────────────────────────────────────────────────────────────
def record(ticker: str, synthesis: dict, panel: dict | None = None) -> None:
    """从 synthesis.json 内容提取三轨分数并追加到历史文件。

    synthesis.json 采用扁平 schema（generate_synthesis 直接输出）：
      overall_score, investment_score, fundamental_score, panel_consensus,
      investment_scorecard (含 axes), market 等顶层 key。

    Args:
        ticker:    股票代码，如 "AAPL" / "600519.SH"
        synthesis: synthesis.json 解析后的 dict（顶层扁平结构）
        panel:     panel.json 解析后的 dict（可选），用于补充 active_count / polarize_k
    """
    try:
        scorecard = synthesis.get("investment_scorecard") or {}
        panel     = panel or {}
        vd        = panel.get("vote_distribution") or {}
        cf        = panel.get("consensus_formula") or {}

        entry = {
            "ts":              datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "ticker":          ticker,
            "market":          synthesis.get("market", ""),
            # 三轨核心分 — 直接读 synthesis 顶层扁平 key
            "overall":         synthesis.get("overall_score"),
            "buy_score":       synthesis.get("investment_score"),
            "fundamental":     synthesis.get("fundamental_score"),
            # 子轴（investment scorecard）
            "axes":            scorecard.get("axes"),
            # panel（从 panel.json 补充；synthesis 不含这些细节）
            "panel_consensus": synthesis.get("panel_consensus"),
            "active_count":    (vd.get("strongly_buy", 0) + vd.get("buy", 0)
                                + vd.get("watch", 0) + vd.get("wait", 0)
                                + vd.get("avoid", 0)) or None,
            # 诊断
            "polarize_k":      cf.get("polarize_k"),
        }
        with _history_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        # 不能让日志写入失败影响主流程
        print(f"⚠️  score_drift.record() 失败（忽略）: {exc}")


# ── 读取 ──────────────────────────────────────────────────────────────────────
def _load_history(ticker: str) -> list[dict]:
    path = _history_path()
    if not path.exists():
        return []
    entries = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("ticker", "").upper() == ticker.upper():
                entries.append(obj)
    return entries


# ── 漂移报告 ──────────────────────────────────────────────────────────────────
_DRIFT_THRESHOLD = 3.0   # ≥ 3 分视为"显著漂移"


def report(ticker: str) -> None:
    """打印 ticker 的评分历史及漂移标注。"""
    history = _load_history(ticker)
    if not history:
        print(f"📊 {ticker}: 暂无历史记录（首次运行会自动建立）。")
        return

    header = f"\n{'═'*70}\n📊 评分漂移报告：{ticker}  ({len(history)} 次记录)\n{'═'*70}"
    print(header)
    # 表头
    cols = ["时间 (UTC)", "overall", "buy_score", "fundamental", "panel", "K"]
    widths = [20, 9, 10, 13, 7, 5]
    header_row = "  ".join(c.ljust(w) for c, w in zip(cols, widths))
    print(header_row)
    print("-" * 70)

    prev: dict | None = None
    for entry in history:
        ts    = (entry.get("ts") or "")[:19].replace("T", " ")
        ov    = entry.get("overall")
        bs    = entry.get("buy_score")
        fd    = entry.get("fundamental")
        pc    = entry.get("panel_consensus")
        pk    = entry.get("polarize_k")

        def _fmt(v: object, prev_v: object) -> str:
            if v is None:
                return "—".ljust(9)
            s = f"{v:.1f}"
            if prev_v is not None:
                delta = float(v) - float(prev_v)
                if abs(delta) >= _DRIFT_THRESHOLD:
                    arrow = "▲" if delta > 0 else "▼"
                    s += f" {arrow}{abs(delta):.1f}⚠"
            return s

        p_ov = prev.get("overall")        if prev else None
        p_bs = prev.get("buy_score")      if prev else None
        p_fd = prev.get("fundamental")    if prev else None
        p_pc = prev.get("panel_consensus") if prev else None

        row = [
            ts.ljust(widths[0]),
            _fmt(ov, p_ov).ljust(widths[1]),
            _fmt(bs, p_bs).ljust(widths[2]),
            _fmt(fd, p_fd).ljust(widths[3]),
            _fmt(pc, p_pc).ljust(widths[4]),
            (f"{pk:.2f}" if pk else "—").ljust(widths[5]),
        ]
        print("  ".join(row))
        prev = entry

    # 摘要
    ovals = [e["overall"] for e in history if e.get("overall") is not None]
    if len(ovals) >= 2:
        drift = max(ovals) - min(ovals)
        print(f"\n  overall 最大漂移 = {drift:.1f} 分 | 最新 = {ovals[-1]:.1f} | 首次 = {ovals[0]:.1f}")
        if drift >= 5:
            print("  ⚠️  漂移 ≥ 5 分，建议检查：权重变更 / 数据质量 / 评委规则 / 维度 stub 修复")

    print("═" * 70)
