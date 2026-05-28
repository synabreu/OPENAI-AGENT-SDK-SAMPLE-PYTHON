"""Hello world example with Agents SDK tracing enabled.

이 파일은 OpenAI Agents SDK의 `trace()`를 사용해 가장 작은 에이전트
실행 흐름을 디버깅하는 예제입니다.

핵심 목표:
1. `Agent`와 `Runner.run()`으로 기본 에이전트를 실행한다.
2. 실행 구간을 `trace()`로 감싸 OpenAI Platform에서 흐름을 확인할 수 있게 한다.
3. trace id, workflow name, final output, token usage를 콘솔에 출력해 로컬 로그와
   대시보드 trace를 서로 연결하기 쉽게 만든다.

실행 전 준비:
    export OPENAI_API_KEY="sk-..."

실행:
    python examples/basic/hello_world_trace.py
"""

from __future__ import annotations

import asyncio
import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    """로컬 개발 환경을 구성합니다.

    이 저장소를 editable install 하지 않은 상태에서도 예제를 바로 실행할 수
    있도록, 현재 파일의 상위 디렉터리를 올라가며 프로젝트 루트를 찾습니다.

    동작:
    1. `src/`가 있는 디렉터리를 찾으면 프로젝트 루트와 `src/`를 `sys.path`에 추가합니다.
    2. `.venv`가 있으면 가상환경의 `site-packages`도 `sys.path`에 추가합니다.
    3. `.env`가 있으면 `KEY=VALUE` 형식의 값을 환경 변수로 로드합니다.

    주의:
    - 이미 설정된 환경 변수는 덮어쓰지 않습니다.
    - 첫 번째로 발견한 `.env`만 읽습니다.
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


def _require_api_key() -> None:
    """OPENAI_API_KEY가 설정되어 있는지 확인합니다.

    Agents SDK는 내부적으로 OpenAI API를 호출하므로 API 키가 필요합니다.
    키가 없을 때 import나 agent 실행 중간에서 애매하게 실패하는 것보다,
    실행 시작 시점에 명확한 메시지로 알려주는 편이 디버깅하기 좋습니다.
    """

    if not _os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            'Set it first, for example: export OPENAI_API_KEY="sk-..."'
        )


# 예제를 로컬에서 직접 실행할 때 이 저장소의 `src/agents` 패키지를
# 우선 사용하도록 환경을 정비합니다.
_load_repo_env()

from agents import Agent, Runner, RunResult, Usage, gen_trace_id, trace


WORKFLOW_NAME = "hello_world_trace_debug"


def print_usage_summary(usage: Usage) -> None:
    """Agents SDK 실행 전체의 token 사용량을 출력합니다.

    Args:
        usage: `result.context_wrapper.usage`에 들어 있는 누적 사용량입니다.

    Debugging notes:
        - 전체 run에 대한 합산 값을 빠르게 보고 싶을 때 사용합니다.
        - tool 호출이나 multi-turn 실행이 있으면 여러 model request의 합산이 됩니다.
    """

    print("\n=== Usage summary ===")
    print("input_tokens:", usage.input_tokens)
    print("output_tokens:", usage.output_tokens)
    print("total_tokens:", usage.total_tokens)
    print("requests:", usage.requests)


def print_raw_response_usage(result: RunResult) -> None:
    """각 모델 응답별 response id, request id, token 사용량을 출력합니다.

    Args:
        result: `Runner.run()`이 반환한 실행 결과입니다.

    Debugging notes:
        - `response_id`는 Responses API의 응답 식별자입니다.
        - `request_id`는 transport request id이며 장애 분석에 유용합니다.
        - raw response별 token을 보면 어떤 모델 호출에서 비용이 발생했는지
          더 세밀하게 확인할 수 있습니다.
    """

    print("\n=== Raw response usage ===")
    print("last_response_id:", result.last_response_id)
    print("raw_response_count:", len(result.raw_responses))

    for index, response in enumerate(result.raw_responses, start=1):
        print(f"raw_response[{index}].response_id:", response.response_id)
        print(f"raw_response[{index}].request_id:", response.request_id)
        print(f"raw_response[{index}].input_tokens:", response.usage.input_tokens)
        print(f"raw_response[{index}].output_tokens:", response.usage.output_tokens)
        print(f"raw_response[{index}].total_tokens:", response.usage.total_tokens)


async def run_traced_agent() -> RunResult:
    """trace로 감싼 Agents SDK hello world 실행을 수행합니다.

    Returns:
        Agents SDK의 `RunResult` 객체입니다.

    Debugging notes:
        - `trace_id`는 로컬 로그와 OpenAI Platform의 trace 화면을 연결하는
          식별자입니다.
        - `workflow_name`은 대시보드에서 여러 실행을 구분하기 쉬운 이름입니다.
        - `Runner.run()` 안에서 모델 호출, tool 호출, handoff 등이 발생하면
          trace의 span으로 기록되어 흐름을 따라갈 수 있습니다.
    """

    _require_api_key()

    # 명시적인 trace id를 만들면 콘솔 로그와 대시보드의 trace를 매칭하기 쉽습니다.
    trace_id = gen_trace_id()

    agent = Agent(
        name="Traceable Assistant",
        instructions=(
            "You are a concise assistant. "
            "Answer in Korean with one short sentence."
        ),
    )

    print("workflow_name:", WORKFLOW_NAME)
    print("trace_id:", trace_id)

    # 이 with 블록 안에서 발생하는 Agents SDK 실행은 하나의 trace로 묶입니다.
    # OpenAI Platform의 traces/logs 화면에서 workflow_name 또는 trace_id를
    # 기준으로 해당 실행을 찾아볼 수 있습니다.
    with trace(workflow_name=WORKFLOW_NAME, trace_id=trace_id):
        result = await Runner.run(
            agent,
            "Say hello and mention that tracing is enabled.",
        )

    return result


async def main() -> None:
    """비동기 스크립트 진입점입니다.

    Agents SDK의 `Runner.run()`은 비동기 함수이므로 `asyncio.run()`으로
    실행합니다. 예제의 출력은 두 종류입니다.

    1. 로컬 디버깅용 메타데이터: workflow name, trace id
    2. 실제 모델 최종 응답: final_output
    3. token 사용량: input_tokens, output_tokens, total_tokens
    """

    result = await run_traced_agent()
    print("final_output:", result.final_output)
    print_usage_summary(result.context_wrapper.usage)
    print_raw_response_usage(result)


if __name__ == "__main__":
    asyncio.run(main())
