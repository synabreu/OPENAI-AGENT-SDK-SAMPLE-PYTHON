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

from pydantic import BaseModel, Field

from agents import Agent, Runner

"""
This example shows structured input for agent-as-tool calls.
"""


class TranslationInput(BaseModel):
    text: str = Field(description="Text to translate.")
    source: str = Field(description="Source language code or name.")
    target: str = Field(description="Target language code or name.")


translator = Agent(
    name="translator",
    instructions=(
        "Translate the input text into the target language. "
        "If the target is not clear, ask the user for clarification."
    ),
)

orchestrator = Agent(
    name="orchestrator",
    instructions=(
        "You are a task dispatcher. Always call the tool with sufficient input. "
        "Do not handle the translation yourself."
    ),
    tools=[
        translator.as_tool(
            tool_name="translate_text",
            tool_description=(
                "Translate text between languages. Provide text, source language, "
                "and target language."
            ),
            parameters=TranslationInput,
            # By default, the input schema will be included in a simpler format.
            # Set include_input_schema to true to include the full JSON Schema:
            # include_input_schema=True,
            # Build a custom prompt from structured input data:
            # input_builder=lambda options: (
            #     f'Translate the text "{options["params"]["text"]}" '
            #     f'from {options["params"]["source"]} to {options["params"]["target"]}.'
            # ),
        )
    ],
)


async def main() -> None:
    query = 'Translate "Hola" from Spanish to French.'

    response1 = await Runner.run(translator, query)
    print(f"Translator agent direct run: {response1.final_output}")

    response2 = await Runner.run(orchestrator, query)
    print(f"Translator agent as tool: {response2.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
