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
    DockerVolumeMountStrategy,
    InContainerMountStrategy,
    MountpointMountPattern,
    RcloneMountPattern,
    S3Mount,
)
from examples.sandbox.docker.mounts.mount_smoke import (
    MountSmokeCase,
    require_env,
    run_mount_smoke_test,
)


def _mount_cases() -> list[MountSmokeCase]:
    bucket = require_env("S3_MOUNT_BUCKET")
    return [
        MountSmokeCase(
            name="docker_volume/rclone",
            mount_dir="s3-docker-volume-rclone",
            mount=S3Mount(
                bucket=bucket,
                access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                session_token=os.getenv("AWS_SESSION_TOKEN"),
                prefix=os.getenv("S3_MOUNT_PREFIX"),
                region=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
                endpoint_url=os.getenv("S3_ENDPOINT_URL"),
                mount_strategy=DockerVolumeMountStrategy(driver="rclone"),
                read_only=False,
            ),
        ),
        MountSmokeCase(
            name="in_container/rclone",
            mount_dir="s3-in-container-rclone",
            mount=S3Mount(
                bucket=bucket,
                access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                session_token=os.getenv("AWS_SESSION_TOKEN"),
                prefix=os.getenv("S3_MOUNT_PREFIX"),
                region=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
                endpoint_url=os.getenv("S3_ENDPOINT_URL"),
                mount_strategy=InContainerMountStrategy(pattern=RcloneMountPattern()),
                read_only=False,
            ),
        ),
        MountSmokeCase(
            name="in_container/mountpoint",
            mount_dir="s3-in-container-mountpoint",
            mount=S3Mount(
                bucket=bucket,
                access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                session_token=os.getenv("AWS_SESSION_TOKEN"),
                prefix=os.getenv("S3_MOUNT_PREFIX"),
                region=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
                endpoint_url=os.getenv("S3_ENDPOINT_URL"),
                mount_strategy=InContainerMountStrategy(pattern=MountpointMountPattern()),
                read_only=False,
            ),
        ),
    ]


async def main() -> None:
    await run_mount_smoke_test(
        provider="s3",
        agent_name="S3 Mount Smoke Test",
        mount_cases=_mount_cases(),
    )


if __name__ == "__main__":
    asyncio.run(main())
