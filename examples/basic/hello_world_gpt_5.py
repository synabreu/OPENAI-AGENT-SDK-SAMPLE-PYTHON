import asyncio

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

from agents import Agent, Runner, ModelSettings
from openai.types.shared import Reasoning


async def main():
    agent = Agent(
        name="Knowledgable GPT-5 Assistant",
        instructions="You're a knowledgable assistant. You always provide an interesting answer.",
        model="gpt-5.5",
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="low"),  # "none", "low", "medium", "high", "xhigh"
            verbosity="low",  # "low", "medium", "high"
        ),
    )
    result = await Runner.run(agent, "Tell me something about recursion in programming.")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
