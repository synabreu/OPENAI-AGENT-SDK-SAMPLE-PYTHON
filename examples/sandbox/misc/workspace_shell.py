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


from agents.sandbox import Capability, Manifest
from agents.sandbox.session.base_sandbox_session import BaseSandboxSession
from agents.tool import (
    ShellCallOutcome,
    ShellCommandOutput,
    ShellCommandRequest,
    ShellResult,
    ShellTool,
    Tool,
)


class WorkspaceShellCapability(Capability):
    """Expose one shell tool for inspecting the active sandbox workspace."""

    def __init__(self) -> None:
        super().__init__(type="workspace_shell")
        self._session: BaseSandboxSession | None = None

    def bind(self, session: BaseSandboxSession) -> None:
        self._session = session

    def tools(self) -> list[Tool]:
        return [ShellTool(executor=self._execute_shell)]

    async def instructions(self, manifest: Manifest) -> str | None:
        _ = manifest
        return (
            "Use the `shell` tool to inspect the sandbox workspace before answering. "
            "The workspace root is the current working directory, so prefer relative paths "
            "with commands like `pwd`, `find .`, and `cat`. Only cite files you actually read."
        )

    async def _execute_shell(self, request: ShellCommandRequest) -> ShellResult:
        if self._session is None:
            raise RuntimeError("Workspace shell is not bound to a sandbox session.")

        timeout_s = (
            request.data.action.timeout_ms / 1000
            if request.data.action.timeout_ms is not None
            else None
        )
        outputs: list[ShellCommandOutput] = []
        for command in request.data.action.commands:
            result = await self._session.exec(command, timeout=timeout_s, shell=True)
            outputs.append(
                ShellCommandOutput(
                    command=command,
                    stdout=result.stdout.decode("utf-8", errors="replace"),
                    stderr=result.stderr.decode("utf-8", errors="replace"),
                    outcome=ShellCallOutcome(type="exit", exit_code=result.exit_code),
                )
            )
        return ShellResult(output=outputs)
