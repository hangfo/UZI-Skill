#!/usr/bin/env python3
"""Minimal stdlib test-function runner for environments without pytest.

Supports the two fixtures used by the bounded UZI validation suite:
``monkeypatch`` (setattr/setenv/delenv/chdir) and ``tmp_path``.  It is intentionally not a
pytest replacement; unsupported fixtures fail explicitly instead of being
silently skipped.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import inspect
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "deep-analysis" / "scripts"
for path in (str(SCRIPTS), str(ROOT), str(ROOT / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)


class MonkeyPatch:
    def __init__(self) -> None:
        self._undo: list[tuple[str, Any]] = []

    def setattr(self, target: Any, name: Any, value: Any = ..., raising: bool = True) -> None:
        if isinstance(target, str):
            if value is not ...:
                raise TypeError("dotted-path setattr accepts target and value only")
            module_name, attr_name = target.rsplit(".", 1)
            target = importlib.import_module(module_name)
            value = name
            name = attr_name
        elif value is ...:
            raise TypeError("object setattr requires target, name and value")
        existed = hasattr(target, name)
        if not existed and raising:
            raise AttributeError(name)
        old = getattr(target, name, None)
        setattr(target, name, value)
        self._undo.append(("attr", (target, name, existed, old)))

    def setitem(self, mapping: Any, name: Any, value: Any) -> None:
        existed = name in mapping
        old = mapping.get(name)
        mapping[name] = value
        self._undo.append(("item", (mapping, name, existed, old)))

    def setenv(self, name: str, value: str) -> None:
        existed = name in os.environ
        old = os.environ.get(name)
        os.environ[name] = str(value)
        self._undo.append(("env", (name, existed, old)))

    def delenv(self, name: str, raising: bool = True) -> None:
        existed = name in os.environ
        if not existed:
            if raising:
                raise KeyError(name)
            return
        old = os.environ.pop(name)
        self._undo.append(("env", (name, True, old)))

    def chdir(self, path: str | os.PathLike[str]) -> None:
        old = Path.cwd()
        os.chdir(path)
        self._undo.append(("cwd", old))

    def undo(self) -> None:
        for kind, payload in reversed(self._undo):
            if kind == "attr":
                target, name, existed, old = payload
                if existed:
                    setattr(target, name, old)
                else:
                    delattr(target, name)
            elif kind == "env":
                name, existed, old = payload
                if existed:
                    os.environ[name] = old
                else:
                    os.environ.pop(name, None)
            elif kind == "item":
                mapping, name, existed, old = payload
                if existed:
                    mapping[name] = old
                else:
                    mapping.pop(name, None)
            else:
                os.chdir(payload)
        self._undo.clear()


def _load(path: Path) -> ModuleType:
    name = f"uzi_direct_{path.stem}_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_file(path: Path) -> tuple[int, list[str]]:
    module = _load(path)
    tests = [
        (name, obj) for name, obj in vars(module).items()
        if name.startswith("test_") and inspect.isfunction(obj)
    ]
    failures: list[str] = []
    for name, func in tests:
        patch = MonkeyPatch()
        temp = Path(tempfile.mkdtemp(prefix="uzi-direct-test-"))
        try:
            fixtures: dict[str, Any] = {
                "monkeypatch": patch,
                "tmp_path": temp,
                "capsys": None,
            }
            required = list(inspect.signature(func).parameters)
            unsupported = [item for item in required if item not in fixtures]
            if unsupported:
                raise RuntimeError(f"unsupported fixtures: {unsupported}")
            func(**{item: fixtures[item] for item in required})
        except Exception as exc:  # assertion details are preserved in the label
            failures.append(f"{path.name}::{name}: {type(exc).__name__}: {exc}")
        finally:
            patch.undo()
            shutil.rmtree(temp, ignore_errors=True)
    return len(tests), failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    total = 0
    failures: list[str] = []
    for path in args.files:
        count, file_failures = run_file(path.resolve())
        total += count
        failures.extend(file_failures)
    passed = total - len(failures)
    print(f"direct tests: {passed}/{total} passed")
    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
