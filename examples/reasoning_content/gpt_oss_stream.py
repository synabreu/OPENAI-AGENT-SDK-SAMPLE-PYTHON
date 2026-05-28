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

from openai import AsyncOpenAI
from openai.types.shared import Reasoning

from agents import (
    Agent,
    ModelSettings,
    OpenAIChatCompletionsModel,
    Runner,
    set_tracing_disabled,
)

set_tracing_disabled(True)

# import logging
# logging.basicConfig(level=logging.DEBUG)

gpt_oss_model = OpenAIChatCompletionsModel(
    model="openai/gpt-oss-20b",
    openai_client=AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
)


async def main():
    agent = Agent(
        name="Assistant",
        instructions="You're a helpful assistant. You provide a concise answer to the user's question.",
        model=gpt_oss_model,
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="high", summary="detailed"),
        ),
    )

    result = Runner.run_streamed(agent, "Tell me about recursion in programming.")
    print("=== Run starting ===")
    print("\n")
    async for event in result.stream_events():
        if event.type == "raw_response_event":
            if event.data.type == "response.reasoning_text.delta":
                print(f"\033[33m{event.data.delta}\033[0m", end="", flush=True)
            elif event.data.type == "response.output_text.delta":
                print(f"\033[32m{event.data.delta}\033[0m", end="", flush=True)

    print("\n")
    print("=== Run complete ===")


if __name__ == "__main__":
    asyncio.run(main())
