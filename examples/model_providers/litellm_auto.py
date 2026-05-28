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

from pydantic import BaseModel

from agents import Agent, ModelSettings, Runner, function_tool, set_tracing_disabled

"""This example uses the built-in support for LiteLLM through OpenRouter.

Set OPENROUTER_API_KEY before running it.
"""

set_tracing_disabled(disabled=True)

# import logging
# logging.basicConfig(level=logging.DEBUG)


@function_tool
def get_weather(city: str):
    print(f"[debug] getting weather for {city}")
    return f"The weather in {city} is sunny."


class Result(BaseModel):
    output_text: str
    tool_results: list[str]


async def main():
    agent = Agent(
        name="Assistant",
        instructions="You only respond in haikus.",
        # We prefix with litellm/ to tell the Runner to use the LitellmModel
        model="litellm/openrouter/openai/gpt-5.4-mini",
        tools=[get_weather],
        model_settings=ModelSettings(tool_choice="required"),
        output_type=Result,
    )

    result = await Runner.run(agent, "What's the weather in Tokyo?")
    print(result.final_output)


if __name__ == "__main__":
    import os

    if os.getenv("OPENROUTER_API_KEY") is None:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. Please set the environment variable and try again."
        )

    asyncio.run(main())
