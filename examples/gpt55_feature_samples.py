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


import argparse
import asyncio
import os
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from openai.types.responses import ResponseTextDeltaEvent
from openai.types.shared import Reasoning
from pydantic import BaseModel, Field

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    ModelSettings,
    RawResponsesStreamEvent,
    RunContextWrapper,
    Runner,
    SQLiteSession,
    TResponseInputItem,
    function_tool,
    input_guardrail,
    trace,
)

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")
VERBOSITY = os.getenv("OPENAI_VERBOSITY", "low")
ARTIFACT_DIR = Path(__file__).resolve().parent.parent / ".tmp" / "gpt55-feature-samples"


def model_settings() -> ModelSettings:
    return ModelSettings(
        reasoning=Reasoning(effort=REASONING_EFFORT),
        verbosity=VERBOSITY,
    )


def agent(
    *,
    name: str,
    instructions: str,
    tools: list | None = None,
    handoffs: list[Agent] | None = None,
    output_type: type[BaseModel] | None = None,
    input_guardrails: list | None = None,
) -> Agent:
    return Agent(
        name=name,
        instructions=instructions,
        model=MODEL,
        model_settings=model_settings(),
        tools=tools or [],
        handoffs=handoffs or [],
        output_type=output_type,
        input_guardrails=input_guardrails or [],
    )


def require_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY is not set. Add it to .env or export it before running samples.",
            file=sys.stderr,
        )
        raise SystemExit(2)


async def sample_hello() -> None:
    assistant = agent(
        name="GPT-5.5 hello",
        instructions="Answer in Korean in two concise sentences.",
    )
    result = await Runner.run(assistant, "OpenAI Agents SDK가 어떤 문제를 해결하나요?")
    print(result.final_output)


class Weather(BaseModel):
    city: str
    temperature_range: str
    conditions: str


@function_tool
def get_weather(city: Annotated[str, "City name"]) -> Weather:
    """Return deterministic demo weather for a city."""
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind")


async def sample_tools() -> None:
    assistant = agent(
        name="GPT-5.5 tool user",
        instructions="Use tools when they are relevant, then answer briefly.",
        tools=[get_weather],
    )
    result = await Runner.run(assistant, "What's the weather in Tokyo?")
    print(result.final_output)


class TravelPlan(BaseModel):
    destination: str = Field(description="Recommended destination")
    days: int = Field(description="Trip length in days")
    reason: str = Field(description="Short reason for the recommendation")


async def sample_structured_output() -> None:
    planner = agent(
        name="GPT-5.5 structured planner",
        instructions="Return a practical compact travel recommendation.",
        output_type=TravelPlan,
    )
    result = await Runner.run(planner, "Plan a short food-focused trip in Japan.")
    print(result.final_output_as(TravelPlan).model_dump_json(indent=2))


async def sample_handoff() -> None:
    korean_agent = agent(name="korean_agent", instructions="Reply only in Korean.")
    english_agent = agent(name="english_agent", instructions="Reply only in English.")
    triage_agent = agent(
        name="triage_agent",
        instructions="Handoff to the agent matching the user's requested response language.",
        handoffs=[korean_agent, english_agent],
    )
    result = await Runner.run(
        triage_agent,
        "한국어로, handoff가 무엇인지 한 문장으로 설명해줘.",
    )
    print(f"Final agent: {result.last_agent.name}")
    print(result.final_output)


async def sample_agents_as_tools() -> None:
    spanish_agent = agent(
        name="spanish_agent",
        instructions="Translate the user's text to Spanish. Return only the translation.",
    )
    french_agent = agent(
        name="french_agent",
        instructions="Translate the user's text to French. Return only the translation.",
    )
    orchestrator = agent(
        name="translation_orchestrator",
        instructions=(
            "Use the provided translation tools. If multiple languages are requested, "
            "call each relevant tool and combine the results."
        ),
        tools=[
            spanish_agent.as_tool(
                tool_name="translate_to_spanish",
                tool_description="Translate text to Spanish.",
            ),
            french_agent.as_tool(
                tool_name="translate_to_french",
                tool_description="Translate text to French.",
            ),
        ],
    )
    result = await Runner.run(orchestrator, "Translate 'Good morning' to Spanish and French.")
    print(result.final_output)


class HomeworkCheck(BaseModel):
    is_homework: bool
    reason: str


guardrail_agent = agent(
    name="homework_guardrail",
    instructions="Detect whether the user is asking you to solve homework for them.",
    output_type=HomeworkCheck,
)


@input_guardrail
async def homework_guardrail(
    context: RunContextWrapper[None],
    current_agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=context.context)
    check = result.final_output_as(HomeworkCheck)
    return GuardrailFunctionOutput(output_info=check, tripwire_triggered=check.is_homework)


async def sample_guardrails() -> None:
    assistant = agent(
        name="guarded_tutor",
        instructions="Help with concepts, but do not solve homework directly.",
        input_guardrails=[homework_guardrail],
    )
    try:
        result = await Runner.run(assistant, "Solve this homework: 2x + 5 = 11")
        print(result.final_output)
    except InputGuardrailTripwireTriggered as exc:
        print("Input guardrail tripped.")
        print(exc.guardrail_result.output.output_info)


async def sample_streaming() -> None:
    assistant = agent(
        name="streaming_assistant",
        instructions="Answer in Korean with a short numbered list.",
    )
    result = Runner.run_streamed(
        assistant,
        "Agents SDK streaming을 쓸 때 좋은 점 3가지를 알려줘.",
    )
    async for event in result.stream_events():
        if isinstance(event, RawResponsesStreamEvent) and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            print(event.data.delta, end="", flush=True)
    print()


async def sample_memory() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    db_path = ARTIFACT_DIR / "sessions.sqlite"
    session = SQLiteSession("vscode-gpt55-demo", db_path=db_path)
    assistant = agent(
        name="memory_assistant",
        instructions="Reply concisely and use prior session context when available.",
    )
    first = await Runner.run(assistant, "My favorite database is SQLite.", session=session)
    print(f"Turn 1: {first.final_output}")
    second = await Runner.run(assistant, "What database did I say I liked?", session=session)
    print(f"Turn 2: {second.final_output}")
    print(f"Session DB: {db_path}")
    await session.close()


async def sample_tracing() -> None:
    assistant = agent(
        name="traced_assistant",
        instructions="Answer in one sentence.",
    )
    with trace("GPT-5.5 VSCode tracing sample"):
        result = await Runner.run(assistant, "What does tracing show in the Agents SDK?")
    print(result.final_output)
    print("Trace was submitted when tracing is enabled for your API key/project.")


SAMPLES: dict[str, Callable[[], Awaitable[None]]] = {
    "hello": sample_hello,
    "tools": sample_tools,
    "structured": sample_structured_output,
    "handoff": sample_handoff,
    "agents-as-tools": sample_agents_as_tools,
    "guardrails": sample_guardrails,
    "streaming": sample_streaming,
    "memory": sample_memory,
    "tracing": sample_tracing,
}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run GPT-5.5 OpenAI Agents SDK feature samples.")
    parser.add_argument(
        "--feature",
        choices=[*SAMPLES.keys(), "all"],
        default="hello",
        help="Feature sample to run.",
    )
    args = parser.parse_args()

    require_api_key()
    print(f"Using model={MODEL}, reasoning={REASONING_EFFORT}, verbosity={VERBOSITY}\n")

    if args.feature == "all":
        for name, sample in SAMPLES.items():
            print(f"\n=== {name} ===")
            await sample()
        return

    await SAMPLES[args.feature]()


if __name__ == "__main__":
    asyncio.run(main())
