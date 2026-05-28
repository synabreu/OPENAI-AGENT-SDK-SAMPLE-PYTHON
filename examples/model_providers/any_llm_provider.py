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

from agents import Agent, Runner, function_tool, set_tracing_disabled
from agents.extensions.models.any_llm_model import AnyLLMModel

"""This example uses the AnyLLMModel directly.

You can run it like this:
uv run examples/model_providers/any_llm_provider.py --model openrouter/openai/gpt-5.4-mini
or
uv run examples/model_providers/any_llm_provider.py --model openrouter/anthropic/claude-4.5-sonnet
"""

set_tracing_disabled(disabled=True)


@function_tool
def get_weather(city: str):
    print(f"[debug] getting weather for {city}")
    return f"The weather in {city} is sunny."


async def main(model: str, api_key: str):
    if api_key == "dummy":
        print("Skipping run because no valid OPENROUTER_API_KEY was provided.")
        return

    agent = Agent(
        name="Assistant",
        instructions="You only respond in haikus.",
        model=AnyLLMModel(model=model, api_key=api_key),
        tools=[get_weather],
    )

    result = await Runner.run(agent, "What's the weather in Tokyo?")
    print(result.final_output)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=False)
    parser.add_argument("--api-key", type=str, required=False)
    args = parser.parse_args()

    model = args.model or os.environ.get("ANY_LLM_MODEL", "openrouter/openai/gpt-5.4-mini")
    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "dummy")

    if not args.model:
        print(f"Using default model: {model}")
    if not args.api_key:
        print("Using OPENROUTER_API_KEY from environment (or dummy placeholder).")

    asyncio.run(main(model, api_key))
