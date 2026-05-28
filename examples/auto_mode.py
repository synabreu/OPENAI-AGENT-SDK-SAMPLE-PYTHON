"""Utilities for running examples in automated mode.

When ``EXAMPLES_INTERACTIVE_MODE=auto`` is set, these helpers provide
deterministic inputs and confirmations so examples can run without manual
interaction. The helpers are intentionally lightweight to avoid adding
dependencies to example code.
"""

from __future__ import annotations

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    for _directory in _Path(__file__).resolve().parents:
        _src_path = _directory / "src"
        if _src_path.exists():
            _root = str(_directory)
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            _src = str(_src_path)
            if _src not in _sys.path:
                _sys.path.insert(0, _src)

        _venv_path = _directory / ".venv"
        if _venv_path.exists():
            _site_packages = next(_venv_path.glob("lib/python*/site-packages"), None)
            if _site_packages is not None:
                _site = str(_site_packages)
                if _site not in _sys.path:
                    _sys.path.insert(1 if _src_path.exists() else 0, _site)

        _env_path = _directory / ".env"
        if not _env_path.exists():
            continue

        for _line in _env_path.read_text().splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _value = _line.split("=", 1)
            _os.environ.setdefault(_key.strip(), _value.strip().strip("\"'"))
        return


_load_repo_env()


import os


def is_auto_mode() -> bool:
    """Return True when examples should bypass interactive prompts."""
    return os.environ.get("EXAMPLES_INTERACTIVE_MODE", "").lower() == "auto"


def input_with_fallback(prompt: str, fallback: str) -> str:
    """Return the fallback text in auto mode, otherwise defer to input()."""
    if is_auto_mode():
        print(f"[auto-input] {prompt.strip()} -> {fallback}")
        return fallback
    return input(prompt)


def confirm_with_fallback(prompt: str, default: bool = True) -> bool:
    """Return default in auto mode; otherwise ask the user."""
    if is_auto_mode():
        choice = "yes" if default else "no"
        print(f"[auto-confirm] {prompt.strip()} -> {choice}")
        return default

    answer = input(prompt).strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}
