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

import argparse
import asyncio
import random

from agents import Agent, GenerateDynamicPromptData, Runner

"""
NOTE: This example will not work out of the box, because the default prompt ID will not be available
in your project.

To use it, please:
1. Go to https://platform.openai.com/playground/prompts
2. Create a new prompt variable, `poem_style`.
3. Create a system prompt with the content:
```
Write a poem in {{poem_style}}
```
4. Run the example with the `--prompt-id` flag.
"""

DEFAULT_PROMPT_ID = "pmpt_6965a984c7ac8194a8f4e79b00f838840118c1e58beb3332"


class DynamicContext:
    def __init__(self, prompt_id: str):
        self.prompt_id = prompt_id
        self.poem_style = random.choice(["limerick", "haiku", "ballad"])
        print(f"[debug] DynamicContext initialized with poem_style: {self.poem_style}")


async def _get_dynamic_prompt(data: GenerateDynamicPromptData):
    ctx: DynamicContext = data.context.context
    return {
        "id": ctx.prompt_id,
        "version": "1",
        "variables": {
            "poem_style": ctx.poem_style,
        },
    }


async def dynamic_prompt(prompt_id: str):
    context = DynamicContext(prompt_id)

    agent = Agent(
        name="Assistant",
        prompt=_get_dynamic_prompt,
    )

    result = await Runner.run(agent, "Tell me about recursion in programming.", context=context)
    print(result.final_output)


async def static_prompt(prompt_id: str):
    agent = Agent(
        name="Assistant",
        prompt={
            "id": prompt_id,
            "version": "1",
            "variables": {
                "poem_style": "limerick",
            },
        },
    )

    result = await Runner.run(agent, "Tell me about recursion in programming.")
    print(result.final_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dynamic", action="store_true")
    parser.add_argument("--prompt-id", type=str, default=DEFAULT_PROMPT_ID)
    args = parser.parse_args()

    if args.dynamic:
        asyncio.run(dynamic_prompt(args.prompt_id))
    else:
        asyncio.run(static_prompt(args.prompt_id))
