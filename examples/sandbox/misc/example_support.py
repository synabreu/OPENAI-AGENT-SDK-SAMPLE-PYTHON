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


from collections.abc import Mapping

from agents.sandbox import Manifest
from agents.sandbox.entries import File


def text_manifest(files: Mapping[str, str]) -> Manifest:
    """Build a manifest from in-memory UTF-8 text files."""

    return Manifest(
        entries={path: File(content=contents.encode("utf-8")) for path, contents in files.items()}
    )


def tool_call_name(raw_item: object) -> str:
    """Return a readable name for a raw tool call item."""

    if isinstance(raw_item, dict):
        name = raw_item.get("name")
        item_type = raw_item.get("type")
    else:
        name = getattr(raw_item, "name", None)
        item_type = getattr(raw_item, "type", None)

    if isinstance(name, str) and name:
        return name
    if item_type == "shell_call":
        return "shell"
    if isinstance(item_type, str):
        return item_type
    return ""
