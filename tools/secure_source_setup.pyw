"""Native Windows masked setup dialog for UZI official data sources."""
from __future__ import annotations

import json
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib.secure_config import configured_keys, save_secure_values  # noqa: E402


FIELDS = (
    ("UZI_SEC_USER_AGENT", "SEC 真实姓名/机构 + 联系邮箱"),
    ("FRED_API_KEY", "FRED API Key"),
    ("MASSIVE_API_KEY", "Massive API Key"),
)


class SetupDialog:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("UZI-Skill 安全数据源配置")
        self.root.geometry("650x365")
        self.root.resizable(False, False)
        self.entries: dict[str, ttk.Entry] = {}
        self.status = tk.StringVar(value="密钥仅保存到当前 Windows 用户的 DPAPI 加密文件。")
        self._build()

    def _build(self) -> None:
        configured = configured_keys()
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="UZI-Skill 官方数据源",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(
            frame,
            text="留空会保留现有值；内容不会写入仓库、.env、终端历史或报告。",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 16))

        for row, (key, label) in enumerate(FIELDS, start=2):
            state = "已配置" if key in configured else "未配置"
            ttk.Label(frame, text=label, width=30).grid(
                row=row, column=0, sticky="w", pady=7
            )
            entry = ttk.Entry(frame, width=45, show="●")
            entry.grid(row=row, column=1, sticky="ew", pady=7)
            self.entries[key] = entry
            ttk.Label(frame, text=state, width=8).grid(
                row=row, column=2, sticky="w", padx=(8, 0)
            )

        ttk.Separator(frame).grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=(14, 10)
        )
        ttk.Label(
            frame,
            textvariable=self.status,
            wraplength=600,
            foreground="#334155",
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 14))

        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, columnspan=3, sticky="e")
        ttk.Button(buttons, text="取消", command=self.root.destroy).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(
            buttons,
            text="保存并真实验证",
            command=self._save_and_validate,
        ).pack(side="right")
        frame.columnconfigure(1, weight=1)

    def _save_and_validate(self) -> None:
        updates = {key: entry.get() for key, entry in self.entries.items()}
        if not any(value.strip() for value in updates.values()) and not configured_keys():
            messagebox.showwarning("没有输入", "请至少填写一个数据源。")
            return
        try:
            save_secure_values(updates)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            return
        for entry in self.entries.values():
            entry.delete(0, "end")
        self.status.set("已加密保存，正在调用三个官方端点做最小真实验证……")
        self.root.update_idletasks()
        command = [
            str(ROOT / ".venv" / "Scripts" / "python.exe"),
            str(ROOT / "tools" / "validate_secure_sources.py"),
            "--network",
            "--json",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            payload = json.loads((completed.stdout or "").strip())
            labels = []
            for name in ("sec", "fred", "massive"):
                item = payload.get("sources", {}).get(name, {})
                labels.append(f"{name.upper()}: {'通过' if item.get('ok') else '失败'}")
            summary = "；".join(labels)
            self.status.set(summary)
            if completed.returncode == 0:
                messagebox.showinfo("验证完成", summary)
            else:
                messagebox.showwarning(
                    "部分数据源未通过",
                    summary + "\n\n不会显示或记录密钥。详细原因由 Codex 做脱敏诊断。",
                )
        except Exception as exc:
            self.status.set("配置已保存；自动验证未完成。")
            messagebox.showwarning("验证未完成", f"配置已加密保存。\n{type(exc).__name__}")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    SetupDialog().run()
