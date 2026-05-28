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
from collections.abc import Mapping
from typing import Any

from agents import Agent, CodeInterpreterTool, Runner, trace


def _get_field(obj: Any, key: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


async def main():
    agent = Agent(
        name="Code interpreter",
        # Note: using gpt-5-class models with streaming for this tool may require org verification.
        # Code interpreter does not support gpt-5 minimal reasoning effort; use default effort.
        model="gpt-5.5",
        instructions=(
            "Always use the code interpreter tool to solve numeric problems, and show the code "
            "you ran when possible."
        ),
        tools=[
            CodeInterpreterTool(
                tool_config={"type": "code_interpreter", "container": {"type": "auto"}},
            )
        ],
    )

    with trace("Code interpreter example"):
        print("Solving math problem with the code interpreter...")
        result = Runner.run_streamed(
            agent,
            (
                "Use the code interpreter tool to calculate the square root of 273 * 312821 + "
                "1782. Show the Python code you ran and then provide the numeric answer."
            ),
        )
        saw_code_interpreter_call = False
        async for event in result.stream_events():
            if event.type != "run_item_stream_event":
                continue

            item = event.item
            if item.type == "tool_call_item":
                raw_call = item.raw_item
                if _get_field(raw_call, "type") == "code_interpreter_call":
                    saw_code_interpreter_call = True
                    code = _get_field(raw_call, "code")
                    if isinstance(code, str):
                        print(f"Code interpreter code:\n```\n{code}\n```\n")
                        continue

            print(f"Other event: {event.item.type}")

        if not saw_code_interpreter_call:
            print("No code_interpreter_call item was emitted.")
        print(f"Final output: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
