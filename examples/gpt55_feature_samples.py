from __future__ import annotations
"""GPT-5.5 기능 샘플 모음.

터미널에서 실행 방법(한글 설명):
1. (선택) 가상환경 활성화:
    source .venv/bin/activate
2. 필요 시 의존성 설치/동기화:
    make sync
3. 샘플 실행(예: hello 샘플):
    python examples/gpt55_feature_samples.py --feature hello
4. 모든 샘플을 연속 실행하려면:
    python examples/gpt55_feature_samples.py --feature all

이 파일은 Agents SDK의 다양한 기능을 시연하는 여러 샘플 함수를 포함합니다.
각 샘플은 독립적으로 실행될 수 있으며, 입출력/스트리밍/가드레일/메모리
등 기능을 보여줍니다.
"""

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


# 함수: 공통 모델 설정(ModelSettings)을 생성하여 반환합니다.
def model_settings() -> ModelSettings:
    """공통 `ModelSettings`를 생성하여 샘플 전체에서 재사용합니다.

    - `REASONING_EFFORT`와 `VERBOSITY` 환경 변수를 반영합니다.
    """
    return ModelSettings(
        reasoning=Reasoning(effort=REASONING_EFFORT),
        verbosity=VERBOSITY,
    )


# 함수: 에이전트 인스턴스를 생성하는 팩토리 함수입니다.
def agent(
    *,
    name: str,
    instructions: str,
    tools: list | None = None,
    handoffs: list[Agent] | None = None,
    output_type: type[BaseModel] | None = None,
    input_guardrails: list | None = None,
    ) -> Agent:
    """에이전트 팩토리 함수.

    - `name`: 에이전트 이름
    - `instructions`: 에이전트에게 줄 지시문
    - `tools`: 에이전트가 사용할 도구 목록
    - `handoffs`: 핸드오프 대상 에이전트 목록
    - `output_type`: 출력 타입(Pydantic 모델) 지정
    - `input_guardrails`: 입력 가드레일 함수 목록
    """
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


# 함수: 환경변수 `OPENAI_API_KEY`가 설정되었는지 확인하고 없으면 종료합니다.
def require_api_key() -> None:
    """환경 변수 `OPENAI_API_KEY`가 설정되어 있지 않으면 종료합니다."""
    if not os.getenv("OPENAI_API_KEY"):
        print(
            "OPENAI_API_KEY is not set. Add it to .env or export it before running samples.",
            file=sys.stderr,
        )
        raise SystemExit(2)


# 함수: 'hello' 샘플을 실행하는 비동기 함수입니다.
async def sample_hello() -> None:
    """간단한 질의응답 샘플: 한국어로 간결하게 답변합니다."""
    assistant = agent(
        name="GPT-5.5 hello",
        instructions="Answer in Korean in two concise sentences.",
    )
    # 에이전트를 실행하고 최종 출력을 출력합니다.
    result = await Runner.run(assistant, "OpenAI Agents SDK가 어떤 문제를 해결하나요?")
    print(result.final_output)


# 클래스: 데모용 날씨 정보를 담는 Pydantic 모델입니다.
class Weather(BaseModel):
    """데모용 날씨 정보를 담는 Pydantic 모델."""
    city: str
    temperature_range: str
    conditions: str


# 함수(도구): 도시 이름을 받아 데모용 날씨 정보를 반환하는 도구입니다.
@function_tool
def get_weather(city: Annotated[str, "City name"]) -> Weather:
    """도시 이름으로 결정론적(예측 가능한) 데모용 날씨 정보를 반환합니다."""
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind")


# 함수: 도구 사용 샘플을 실행하는 비동기 함수입니다.
async def sample_tools() -> None:
    """도구 사용 샘플: 에이전트가 도구를 호출하여 응답을 생성합니다."""
    assistant = agent(
        name="GPT-5.5 tool user",
        instructions="Use tools when they are relevant, then answer briefly.",
        tools=[get_weather],
    )
    # 도구를 통한 질의 실행
    result = await Runner.run(assistant, "What's the weather in Tokyo?")
    print(result.final_output)


# 클래스: 여행 추천의 구조화된 출력을 위한 Pydantic 모델입니다.
class TravelPlan(BaseModel):
    """여행 추천의 구조화된 출력을 위한 Pydantic 모델."""
    destination: str = Field(description="Recommended destination")
    days: int = Field(description="Trip length in days")
    reason: str = Field(description="Short reason for the recommendation")


# 함수: 구조화된 출력 샘플을 실행하는 비동기 함수입니다.
async def sample_structured_output() -> None:
    """구조화된 출력 샘플: Pydantic 모델로 결과를 받는 예시입니다."""
    planner = agent(
        name="GPT-5.5 structured planner",
        instructions="Return a practical compact travel recommendation.",
        output_type=TravelPlan,
    )
    result = await Runner.run(planner, "Plan a short food-focused trip in Japan.")
    # 모델 출력 객체를 `TravelPlan`으로 파싱하여 JSON으로 출력합니다.
    print(result.final_output_as(TravelPlan).model_dump_json(indent=2))


# 함수: 핸드오프 동작을 시연하는 비동기 함수입니다.
async def sample_handoff() -> None:
    """핸드오프 샘플: 사용자 요청에 따라 적절한 에이전트로 핸드오프합니다."""
    korean_agent = agent(name="korean_agent", instructions="Reply only in Korean.")
    english_agent = agent(name="english_agent", instructions="Reply only in English.")
    triage_agent = agent(
        name="triage_agent",
        instructions="Handoff to the agent matching the user's requested response language.",
        handoffs=[korean_agent, english_agent],
    )
    # 핸드오프 실행 후 어떤 에이전트가 최종 응답을 생성했는지 표시합니다.
    result = await Runner.run(
        triage_agent,
        "한국어로, handoff가 무엇인지 한 문장으로 설명해줘.",
    )
    print(f"Final agent: {result.last_agent.name}")
    print(result.final_output)


# 함수: 에이전트를 도구로 사용하는 샘플을 실행하는 비동기 함수입니다.
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
    """에이전트를 도구로 사용하는 샘플: 여러 언어로 번역을 조율합니다."""
    result = await Runner.run(orchestrator, "Translate 'Good morning' to Spanish and French.")
    print(result.final_output)


# 클래스: 숙제 여부 판정 결과를 담는 Pydantic 모델입니다.
class HomeworkCheck(BaseModel):
    """숙제 여부 판정 결과를 담는 모델."""
    is_homework: bool
    reason: str


guardrail_agent = agent(
    name="homework_guardrail",
    instructions="Detect whether the user is asking you to solve homework for them.",
    output_type=HomeworkCheck,
)


# 함수(가드레일): 입력을 검사하여 숙제 해결 요청인지 판정합니다.
@input_guardrail
async def homework_guardrail(
    context: RunContextWrapper[None],
    current_agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    # 가드레일 에이전트로 입력을 검사하고, 결과를 `HomeworkCheck` 모델로 파싱합니다.
    result = await Runner.run(guardrail_agent, input, context=context.context)
    check = result.final_output_as(HomeworkCheck)
    # `tripwire_triggered`를 통해 가드레일 트리거 여부를 전달합니다.
    return GuardrailFunctionOutput(output_info=check, tripwire_triggered=check.is_homework)


# 함수: 입력 가드레일 샘플을 실행하는 비동기 함수입니다.
async def sample_guardrails() -> None:
    """입력 가드레일 샘플: 가드레일이 트리거될 때의 흐름을 보여줍니다."""
    assistant = agent(
        name="guarded_tutor",
        instructions="Help with concepts, but do not solve homework directly.",
        input_guardrails=[homework_guardrail],
    )
    try:
        # 문제 풀이 요청을 시도하면 가드레일이 트리거될 수 있습니다.
        result = await Runner.run(assistant, "Solve this homework: 2x + 5 = 11")
        print(result.final_output)
    except InputGuardrailTripwireTriggered as exc:
        print("Input guardrail tripped.")
        print(exc.guardrail_result.output.output_info)


# 함수: 스트리밍 샘플을 실행하는 비동기 함수입니다.
async def sample_streaming() -> None:
    """스트리밍 샘플: 텍스트 델타를 실시간으로 수신하여 출력합니다."""
    assistant = agent(
        name="streaming_assistant",
        instructions="Answer in Korean with a short numbered list.",
    )
    result = Runner.run_streamed(
        assistant,
        "Agents SDK streaming을 쓸 때 좋은 점 3가지를 알려줘.",
    )
    # 스트리밍 이벤트를 순회하며 텍스트 델타를 출력합니다.
    async for event in result.stream_events():
        if isinstance(event, RawResponsesStreamEvent) and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            print(event.data.delta, end="", flush=True)
    print()


# 함수: 세션(메모리) 샘플을 실행하는 비동기 함수입니다.
async def sample_memory() -> None:
    """메모리(세션) 샘플: SQLiteSession을 이용해 대화 상태를 유지합니다."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    db_path = ARTIFACT_DIR / "sessions.sqlite"
    session = SQLiteSession("vscode-gpt55-demo", db_path=db_path)
    assistant = agent(
        name="memory_assistant",
        instructions="Reply concisely and use prior session context when available.",
    )
    # 첫 번째 턴을 저장한 뒤, 두 번째 턴에서 이전 발언을 참조합니다.
    first = await Runner.run(assistant, "My favorite database is SQLite.", session=session)
    print(f"Turn 1: {first.final_output}")
    second = await Runner.run(assistant, "What database did I say I liked?", session=session)
    print(f"Turn 2: {second.final_output}")
    print(f"Session DB: {db_path}")
    await session.close()


# 함수: 트레이싱 샘플을 실행하는 비동기 함수입니다.
async def sample_tracing() -> None:
    """추적(tracing) 샘플: trace 블록을 사용해 실행을 추적합니다."""
    assistant = agent(
        name="traced_assistant",
        instructions="Answer in one sentence.",
    )
    # trace 컨텍스트 안에서 실행하면 추적 정보가 수집되어 제출됩니다.
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


# 함수: 커맨드라인 인자를 파싱하고 선택된 샘플을 실행하는 진입점입니다.
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
