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


import io
from pathlib import Path

from agents import ApplyPatchTool, apply_diff
from agents.editor import ApplyPatchOperation, ApplyPatchResult
from agents.sandbox import Capability, Manifest
from agents.sandbox.session.base_sandbox_session import BaseSandboxSession
from agents.tool import Tool


def _read_text(handle: io.IOBase) -> str:
    payload = handle.read()
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes | bytearray):
        return bytes(payload).decode("utf-8", errors="replace")
    return str(payload)


class _SandboxWorkspaceEditor:
    def __init__(self, session: BaseSandboxSession) -> None:
        self._session = session

    async def create_file(self, operation: ApplyPatchOperation) -> ApplyPatchResult:
        target = self._resolve_path(operation.path)
        content = apply_diff("", operation.diff or "", mode="create")
        await self._session.mkdir(target.parent, parents=True)
        await self._session.write(target, io.BytesIO(content.encode("utf-8")))
        return ApplyPatchResult(output=f"Created {self._display_path(target)}")

    async def update_file(self, operation: ApplyPatchOperation) -> ApplyPatchResult:
        target = self._resolve_path(operation.path)
        handle = await self._session.read(target)
        try:
            original = _read_text(handle)
        finally:
            handle.close()
        updated = apply_diff(original, operation.diff or "")
        await self._session.write(target, io.BytesIO(updated.encode("utf-8")))
        return ApplyPatchResult(output=f"Updated {self._display_path(target)}")

    async def delete_file(self, operation: ApplyPatchOperation) -> ApplyPatchResult:
        target = self._resolve_path(operation.path)
        await self._session.rm(target)
        return ApplyPatchResult(output=f"Deleted {self._display_path(target)}")

    def _resolve_path(self, raw_path: str) -> Path:
        return self._session.normalize_path(raw_path)

    def _display_path(self, path: Path) -> str:
        root = Path(self._session.state.manifest.root)
        return path.relative_to(root).as_posix()


class WorkspaceApplyPatchCapability(Capability):
    """Expose the hosted apply_patch tool against the active sandbox workspace."""

    def __init__(self) -> None:
        super().__init__(type="workspace_apply_patch")
        self._session: BaseSandboxSession | None = None

    def bind(self, session: BaseSandboxSession) -> None:
        self._session = session

    def tools(self) -> list[Tool]:
        if self._session is None:
            return []
        return [ApplyPatchTool(editor=_SandboxWorkspaceEditor(self._session))]

    async def instructions(self, manifest: Manifest) -> str | None:
        _ = manifest
        return (
            "Use the `apply_patch` tool for workspace text edits when you need to create or "
            "update files inside the sandbox. Prefer saving final outputs in the requested "
            "workspace directories instead of describing edits without writing them."
        )
