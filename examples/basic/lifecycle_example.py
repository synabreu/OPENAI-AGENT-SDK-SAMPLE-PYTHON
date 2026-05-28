import os as _os
import sys as _sys
from pathlib import Path as _Path


"""Lifecycle example for Agents SDK.

이 모듈은 에이전트 실행의 라이프사이클 훅(hooks), 간단한 로컬 함수 도구,
핸드오프(hand-off) 시나리오를 보여주는 예제입니다. 주요 구성 요소:

- `_load_repo_env()` : 로컬 `src/`와 발견된 `.venv`의 `site-packages`를
    `sys.path`에 추가하고 `.env` 파일을 로드하여 예제를 로컬에서 쉽게
    실행할 수 있게 합니다.
- `LoggingHooks`, `ExampleHooks` : 에이전트와 러너의 여러 이벤트에서
    호출되어 상태와 사용량을 출력하는 훅 구현 예시입니다.
- `random_number`, `multiply_by_two` : `@function_tool`로 등록된 간단한
    동기 함수형 도구들입니다.
- `start_agent`, `multiply_agent` : 에이전트 인스턴스 예시. `start_agent`
    가 난수를 생성하고 홀수일 경우 `multiply_agent`로 핸드오프합니다.

아래 예제는 학습/데모 목적이며 실제 프로덕션 사용 시에는 보안과 에러 처리를 강화해야 합니다.

실행 방법

선수 사항:
- (선택) 포함된 .venv를 사용하는 경우 프로젝트의 가상 환경을 활성화하세요:
    source .venv/bin/activate

- (선택) 의존성 설치 또는 동기:
    make sync

예제 실행:

    python examples/basic/lifecycle_example.py

You can also use the project's `uv` runner if configured:
프로젝트에 설정되어 있으면 `uv` runner를 다음과 같이 사용할 수도 있습니다:

    uv run python examples/basic/lifecycle_example.py

샘플 대화형 세션(출력은 달라질 수 있습니다):

$ python examples/basic/lifecycle_example.py
"""

def _load_repo_env() -> None:
    """로컬 개발환경에서 예제 실행을 돕기 위한 보조 로직.

    상위 디렉터리를 순회하며 다음을 수행합니다:
    - `src/`를 발견하면 프로젝트 루트와 `src` 경로를 `sys.path`에 삽입합니다.
    - `.venv`를 발견하면 그 안의 `site-packages`를 `sys.path`에 추가합니다.
    - `.env` 파일을 발견하면 `KEY=VALUE` 형식의 환경변수를 로드합니다.

    첫 번째로 발견된 `.env` 파일을 적용한 뒤 함수를 종료합니다.
    """

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
import random
from typing import Any, cast

from pydantic import BaseModel

from agents import (
    Agent,
    AgentHookContext,
    AgentHooks,
    RunContextWrapper,
    RunHooks,
    Runner,
    Tool,
    Usage,
    function_tool,
)
from agents.items import ModelResponse, TResponseInputItem
from agents.tool_context import ToolContext
from examples.auto_mode import input_with_fallback


class LoggingHooks(AgentHooks[Any]):
    """간단한 로깅 훅 예제.

    에이전트 시작(`on_start`)과 종료(`on_end`) 시에 호출되어 콘솔에
    실행 정보를 출력합니다. 교육용으로 사용됩니다.
    """
    async def on_start(
        self,
        context: AgentHookContext[Any],
        agent: Agent[Any],
    ) -> None:
        # Access the turn_input from the context to see what input the agent received
        print(f"#### {agent.name} is starting with turn_input: {context.turn_input}")

    async def on_end(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        output: Any,
    ) -> None:
        print(f"#### {agent.name} produced output: {output}.")


class ExampleHooks(RunHooks):
    """런타임 훅(RunHooks) 데모 구현.

    이 훅은 에이전트와 LLM, 도구(tool), 핸드오프 이벤트의 시작/종료를
    모니터링하고 이벤트 카운터 및 사용량(Usage)을 출력합니다. 로컬 도구의
    시작/종료 이벤트에서는 `ToolContext`로 캐스트해 추가 정보를 표시합니다.
    """
    def __init__(self):
        self.event_counter = 0

    def _usage_to_str(self, usage: Usage) -> str:
        return f"{usage.requests} requests, {usage.input_tokens} input tokens, {usage.output_tokens} output tokens, {usage.total_tokens} total tokens"

    async def on_agent_start(self, context: AgentHookContext, agent: Agent) -> None:
        self.event_counter += 1
        # Access the turn_input from the context to see what input the agent received
        print(
            f"### {self.event_counter}: Agent {agent.name} started. turn_input: {context.turn_input}. Usage: {self._usage_to_str(context.usage)}"
        )

    async def on_llm_start(
        self,
        context: RunContextWrapper,
        agent: Agent,
        system_prompt: str | None,
        input_items: list[TResponseInputItem],
    ) -> None:
        self.event_counter += 1
        print(f"### {self.event_counter}: LLM started. Usage: {self._usage_to_str(context.usage)}")

    async def on_llm_end(
        self, context: RunContextWrapper, agent: Agent, response: ModelResponse
    ) -> None:
        self.event_counter += 1
        print(f"### {self.event_counter}: LLM ended. Usage: {self._usage_to_str(context.usage)}")

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        self.event_counter += 1
        print(
            f"### {self.event_counter}: Agent {agent.name} ended with output {output}. Usage: {self._usage_to_str(context.usage)}"
        )

    # Note: The on_tool_start and on_tool_end hooks apply only to local tools.
    # They do not include hosted tools that run on the OpenAI server side,
    # such as WebSearchTool, FileSearchTool, CodeInterpreterTool, HostedMCPTool,
    # or other built-in hosted tools.
    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        self.event_counter += 1
        # While this type cast is not ideal,
        # we don't plan to change the context arg type in the near future for backwards compatibility.
        tool_context = cast(ToolContext[Any], context)
        print(
            f"### {self.event_counter}: Tool {tool.name} started. name={tool_context.tool_name}, call_id={tool_context.tool_call_id}, args={tool_context.tool_arguments}. Usage: {self._usage_to_str(tool_context.usage)}"
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str
    ) -> None:
        self.event_counter += 1
        # While this type cast is not ideal,
        # we don't plan to change the context arg type in the near future for backwards compatibility.
        tool_context = cast(ToolContext[Any], context)
        print(
            f"### {self.event_counter}: Tool {tool.name} finished. result={result}, name={tool_context.tool_name}, call_id={tool_context.tool_call_id}, args={tool_context.tool_arguments}. Usage: {self._usage_to_str(tool_context.usage)}"
        )

    async def on_handoff(
        self, context: RunContextWrapper, from_agent: Agent, to_agent: Agent
    ) -> None:
        self.event_counter += 1
        print(
            f"### {self.event_counter}: Handoff from {from_agent.name} to {to_agent.name}. Usage: {self._usage_to_str(context.usage)}"
        )


hooks = ExampleHooks()

###


@function_tool
def random_number(max: int) -> int:
    """0부터 `max`까지(포함) 임의의 정수를 반환하는 도구 함수.

    이 함수는 `@function_tool` 데코레이터로 등록되어 에이전트가 도구로
    호출할 수 있게 됩니다. 예제에서 `Start Agent`가 이 도구를 호출하여
    무작위 숫자를 생성합니다.
    """
    return random.randint(0, max)


@function_tool
def multiply_by_two(x: int) -> int:
    """주어진 정수 `x`를 두 배로 곱한 값을 반환하는 도구 함수.

    `Multiply Agent`에서 사용되며 간단한 동기 함수 도구의 예시입니다.
    """
    return x * 2


class FinalResult(BaseModel):
    """에이전트 출력의 Pydantic 모델 예시.

    이 모델은 최종 결과로 `number` 정수 값을 갖습니다. `Agent`의
    `output_type`으로 사용되어 출력의 검증/직렬화를 도와줍니다.
    """
    number: int


multiply_agent = Agent(
    name="Multiply Agent",
    instructions="Multiply the number by 2 and then return the final result.",
    tools=[multiply_by_two],
    output_type=FinalResult,
    hooks=LoggingHooks(),
)

start_agent = Agent(
    name="Start Agent",
    instructions="Generate a random number. If it's even, stop. If it's odd, hand off to the multiplier agent.",
    tools=[random_number],
    output_type=FinalResult,
    handoffs=[multiply_agent],
    hooks=LoggingHooks(),
)


async def main() -> None:
    """예제의 메인 실행 흐름.

    - 사용자로부터 최대값을 입력받아 정수로 변환합니다(기본값 제공).
    - `Runner.run`을 호출해 `start_agent`를 실행하고 훅(`hooks`)을 전달합니다.
    - 입력값이 정수가 아니면 오류 메시지를 출력하고 종료합니다.
    """

    user_input = input_with_fallback("Enter a max number: ", "50")
    try:
        max_number = int(user_input)
        await Runner.run(
            start_agent,
            hooks=hooks,
            input=f"Generate a random number between 0 and {max_number}.",
        )
    except ValueError:
        print("Please enter a valid integer.")
        return

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())

"""
Enter a max number: 250
### 1: Agent Start Agent started. Usage: 0 requests, 0 input tokens, 0 output tokens, 0 total tokens
### 2: LLM started. Usage: 0 requests, 0 input tokens, 0 output tokens, 0 total tokens
### 3: LLM ended. Usage: 1 requests, 143 input tokens, 15 output tokens, 158 total tokens
### 4: Tool random_number started. name=random_number, call_id=call_IujmDZYiM800H0hy7v17VTS0, args={"max":250}. Usage: 1 requests, 143 input tokens, 15 output tokens, 158 total tokens
### 5: Tool random_number finished. result=107, name=random_number, call_id=call_IujmDZYiM800H0hy7v17VTS0, args={"max":250}. Usage: 1 requests, 143 input tokens, 15 output tokens, 158 total tokens
### 6: LLM started. Usage: 1 requests, 143 input tokens, 15 output tokens, 158 total tokens
### 7: LLM ended. Usage: 2 requests, 310 input tokens, 29 output tokens, 339 total tokens
### 8: Handoff from Start Agent to Multiply Agent. Usage: 2 requests, 310 input tokens, 29 output tokens, 339 total tokens
### 9: Agent Multiply Agent started. Usage: 2 requests, 310 input tokens, 29 output tokens, 339 total tokens
### 10: LLM started. Usage: 2 requests, 310 input tokens, 29 output tokens, 339 total tokens
### 11: LLM ended. Usage: 3 requests, 472 input tokens, 45 output tokens, 517 total tokens
### 12: Tool multiply_by_two started. name=multiply_by_two, call_id=call_KhHvTfsgaosZsfi741QvzgYw, args={"x":107}. Usage: 3 requests, 472 input tokens, 45 output tokens, 517 total tokens
### 13: Tool multiply_by_two finished. result=214, name=multiply_by_two, call_id=call_KhHvTfsgaosZsfi741QvzgYw, args={"x":107}. Usage: 3 requests, 472 input tokens, 45 output tokens, 517 total tokens
### 14: LLM started. Usage: 3 requests, 472 input tokens, 45 output tokens, 517 total tokens
### 15: LLM ended. Usage: 4 requests, 660 input tokens, 56 output tokens, 716 total tokens
### 16: Agent Multiply Agent ended with output number=214. Usage: 4 requests, 660 input tokens, 56 output tokens, 716 total tokens
Done!
"""
