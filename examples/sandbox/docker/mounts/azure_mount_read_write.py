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


import asyncio
import os
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from agents.sandbox.entries import (
    AzureBlobMount,
    DockerVolumeMountStrategy,
    FuseMountPattern,
    InContainerMountStrategy,
    RcloneMountPattern,
)
from examples.sandbox.docker.mounts.mount_smoke import (
    MountSmokeCase,
    require_env,
    run_mount_smoke_test,
)


def _mount_cases() -> list[MountSmokeCase]:
    account = require_env("AZURE_STORAGE_ACCOUNT")
    container = require_env("AZURE_STORAGE_CONTAINER")
    endpoint = os.getenv("AZURE_STORAGE_ENDPOINT")
    identity_client_id = os.getenv("AZURE_CLIENT_ID")
    account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

    return [
        MountSmokeCase(
            name="docker_volume/rclone",
            mount_dir="azure-docker-volume-rclone",
            mount=AzureBlobMount(
                account=account,
                container=container,
                endpoint=endpoint,
                identity_client_id=identity_client_id,
                account_key=account_key,
                mount_strategy=DockerVolumeMountStrategy(driver="rclone"),
                read_only=False,
            ),
        ),
        MountSmokeCase(
            name="in_container/rclone",
            mount_dir="azure-in-container-rclone",
            mount=AzureBlobMount(
                account=account,
                container=container,
                endpoint=endpoint,
                identity_client_id=identity_client_id,
                account_key=account_key,
                mount_strategy=InContainerMountStrategy(pattern=RcloneMountPattern()),
                read_only=False,
            ),
        ),
        MountSmokeCase(
            name="in_container/fuse",
            mount_dir="azure-in-container-fuse",
            mount=AzureBlobMount(
                account=account,
                container=container,
                endpoint=endpoint,
                identity_client_id=identity_client_id,
                account_key=account_key,
                mount_strategy=InContainerMountStrategy(pattern=FuseMountPattern()),
                read_only=False,
            ),
        ),
    ]


async def main() -> None:
    await run_mount_smoke_test(
        provider="azure",
        agent_name="Azure Blob Mount Smoke Test",
        mount_cases=_mount_cases(),
    )


if __name__ == "__main__":
    asyncio.run(main())
