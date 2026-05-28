"""Worker startup diagnostics."""

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


YELLOW = "\033[1;33m"
RESET = "\033[0m"


def print_backend_warnings(registered_names: set[str]) -> None:
    """Print a prominent warning banner for any unconfigured sandbox backends."""
    import docker  # type: ignore[import-untyped]

    backend_env = {
        "daytona": "DAYTONA_API_KEY",
        "e2b": "E2B_API_KEY",
    }
    missing = {name: var for name, var in backend_env.items() if name not in registered_names}
    try:
        docker.from_env().ping()
    except Exception:
        missing["docker"] = "Docker daemon"

    if not missing:
        return

    lines = [
        "WARNING: Some sandbox backends are NOT available.",
        "Missing:",
    ]
    for name, var in sorted(missing.items()):
        lines.append(f"  - {name} ({var})")
    lines.append("The TUI will fail if you select an unconfigured backend.")
    lines.append("To use them, set the missing env vars and restart the worker.")
    width = max(len(line) for line in lines) + 4
    border = "!" * (width + 2)
    print(f"{YELLOW}{border}{RESET}")
    for line in lines:
        print(f"{YELLOW}! {line:<{width - 2}} !{RESET}")
    print(f"{YELLOW}{border}{RESET}")
