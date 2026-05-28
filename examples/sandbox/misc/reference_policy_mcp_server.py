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

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Reference Policy Server")


@mcp.tool()
def get_policy_reference(topic: str) -> str:
    """Return short internal policy guidance for a supported topic."""
    normalized = topic.strip().lower()
    if "discount" in normalized:
        return (
            "Discount policy: discounts from 11 to 15 percent require regional sales director "
            "approval. Discounts above 15 percent require both finance and the regional sales "
            "director."
        )
    if "security" in normalized or "review" in normalized:
        return (
            "Security review policy: any new data export workflow must finish security review "
            "before kickoff or production access."
        )
    return "No policy reference is available for that topic in this demo."


if __name__ == "__main__":
    mcp.run()
