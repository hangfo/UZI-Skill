"""Windows DPAPI-backed local configuration for sensitive data-source values.

The encrypted payload lives outside the repository under LOCALAPPDATA and is
bound to the current Windows user.  Values are loaded into process memory only;
callers must never log or serialize them.
"""
from __future__ import annotations

import base64
import ctypes
import json
import os
import platform
from ctypes import wintypes
from pathlib import Path
from typing import Iterable


SCHEMA = "uzi.secure_sources.v1"
ALLOWED_KEYS = {
    "UZI_SEC_USER_AGENT",
    "FRED_API_KEY",
    "MASSIVE_API_KEY",
}
_ENTROPY = b"UZI-Skill|secure-sources|v1"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def secure_config_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    return Path(base) / "UZI-Skill" / "secure-sources.v1.json"


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("DPAPI secure configuration is available only on Windows")


def _input_blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    blob = _DataBlob(
        len(data),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    return blob, buffer


def _crypt_protect(data: bytes) -> bytes:
    _require_windows()
    source, source_buffer = _input_blob(data)
    entropy, entropy_buffer = _input_blob(_ENTROPY)
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(source),
        None,
        ctypes.byref(entropy),
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output),
    )
    _ = source_buffer, entropy_buffer
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)


def _crypt_unprotect(data: bytes) -> bytes:
    _require_windows()
    source, source_buffer = _input_blob(data)
    entropy, entropy_buffer = _input_blob(_ENTROPY)
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        ctypes.byref(entropy),
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output),
    )
    _ = source_buffer, entropy_buffer
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)


def _read_payload(path: Path | None = None) -> dict:
    target = path or secure_config_path()
    if not target.exists():
        return {"schema": SCHEMA, "values": {}}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("secure source configuration is unreadable") from exc
    if payload.get("schema") != SCHEMA or not isinstance(payload.get("values"), dict):
        raise RuntimeError("secure source configuration schema mismatch")
    return payload


def configured_keys(path: Path | None = None) -> set[str]:
    payload = _read_payload(path)
    return {
        key
        for key, value in payload["values"].items()
        if key in ALLOWED_KEYS and isinstance(value, str) and value
    }


def save_secure_values(
    updates: dict[str, str],
    *,
    path: Path | None = None,
) -> set[str]:
    """Encrypt non-empty updates. Blank values preserve existing entries."""
    target = path or secure_config_path()
    payload = _read_payload(target)
    values = dict(payload["values"])
    for key, value in updates.items():
        if key not in ALLOWED_KEYS:
            raise ValueError(f"unsupported secure configuration key: {key}")
        clean = str(value or "").strip()
        if not clean:
            continue
        encrypted = _crypt_protect(clean.encode("utf-8"))
        values[key] = base64.b64encode(encrypted).decode("ascii")
    target.parent.mkdir(parents=True, exist_ok=True)
    next_payload = {"schema": SCHEMA, "values": values}
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(
        json.dumps(next_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temp, target)
    return configured_keys(target)


def read_secure_values(
    names: Iterable[str] | None = None,
    *,
    path: Path | None = None,
) -> dict[str, str]:
    requested = set(names or ALLOWED_KEYS)
    unsupported = requested - ALLOWED_KEYS
    if unsupported:
        raise ValueError(f"unsupported secure configuration keys: {sorted(unsupported)}")
    payload = _read_payload(path)
    result: dict[str, str] = {}
    for key in requested:
        encoded = payload["values"].get(key)
        if not encoded:
            continue
        try:
            encrypted = base64.b64decode(encoded, validate=True)
            result[key] = _crypt_unprotect(encrypted).decode("utf-8")
        except Exception as exc:
            raise RuntimeError(f"unable to decrypt secure value: {key}") from exc
    return result


def load_secure_config(names: Iterable[str] | None = None) -> set[str]:
    """Load encrypted values into this process without overriding explicit env."""
    if platform.system() != "Windows":
        return set()
    values = read_secure_values(names)
    loaded: set[str] = set()
    for key, value in values.items():
        if key not in os.environ and value:
            os.environ[key] = value
            loaded.add(key)
    return loaded
