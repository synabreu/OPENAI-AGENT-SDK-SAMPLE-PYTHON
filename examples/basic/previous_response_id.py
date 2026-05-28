"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/previous_response_id.py

이 예제는 `previous_response_id`를 사용해 이전 응답을 참조하여 대화를
계속하는 방법을 보여줍니다. 이 기능은 OpenAI Responses API에만 적용됩니다.
"""

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
     """
     로컬 개발 환경 보조 함수.

     상위 디렉터리를 순회하며 `src/`, `.venv`의 site-packages, 그리고 `.env` 파일을
     찾아 `sys.path`와 환경변수를 설정해 예제가 로컬 환경에서 동작하도록 돕습니다.
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

from agents import Agent, Runner
from examples.auto_mode import input_with_fallback, is_auto_mode

"""`previous_response_id` 매개변수를 사용해 대화를 이어가는 방법을 보여줍니다.

두 번째 실행에서는 이전 응답의 ID를 모델에 전달하여 이전 메시지를 다시
전송하지 않고도 대화를 계속할 수 있도록 합니다.

참고:
1. 이 기능은 OpenAI Responses API에만 적용되며, 다른 모델에서는 무시될 수 있습니다.
2. 응답은 작성 시점 기준으로 30일 동안만 저장됩니다. 따라서 운영 환경에서는
    응답 ID와 만료일을 함께 저장하고, 만료된 경우 이전 대화 이력을 다시 전송해야 합니다.
"""


async def main():
    """
    동기(비스트리밍) 예제 실행 함수.

    - 첫 번째 호출에서는 일반적인 질문을 모델에 전달하고 응답을 받습니다.
    - 두 번째 호출에서는 `previous_response_id`에 이전 호출의 `last_response_id`를
      전달하여 모델이 대화를 이어가도록 합니다(이전 메시지 재전송 불필요).
    """

    print("=== Non-streaming Example ===")

    # 에이전트 생성: 간단한 지침을 전달합니다.
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant. be VERY concise.",
    )

    # 첫 번째 요청을 실행하고 최종 출력과 last_response_id를 확인합니다.
    result = await Runner.run(agent, "What is the largest country in South America?")
    print(result.final_output)
    # 예상 출력 예: Brazil

    # 이전 응답 ID를 사용해 대화를 이어갑니다.
    result = await Runner.run(
        agent,
        "What is the capital of that country?",
        previous_response_id=result.last_response_id,
    )
    print(result.final_output)
    # 예상 출력 예: Brasilia


async def main_stream():
    """
    스트리밍 예제 실행 함수.

    - 스트리밍 모드로 첫 번째 질의를 전송하고 스트림 이벤트를 출력합니다.
    - 이전 응답 ID를 사용해 두 번째 스트리밍 호출에서 대화를 이어갑니다.
    """

    print("=== Streaming Example ===")

    # 에이전트 생성
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant. be VERY concise.",
    )

    # 스트리밍 실행: 첫 번째 질의를 스트리밍으로 실행하고 이벤트를 순회하여 출력합니다.
    result = Runner.run_streamed(agent, "What is the largest country in South America?")

    async for event in result.stream_events():
        if event.type == "raw_response_event" and event.data.type == "response.output_text.delta":
            print(event.data.delta, end="", flush=True)

    print()

    # 이전 응답 ID를 사용해 스트리밍 모드에서 대화를 이어갑니다.
    result = Runner.run_streamed(
        agent,
        "What is the capital of that country?",
        previous_response_id=result.last_response_id,
    )

    async for event in result.stream_events():
        if event.type == "raw_response_event" and event.data.type == "response.output_text.delta":
            print(event.data.delta, end="", flush=True)


if __name__ == "__main__":
    # 스크립트를 직접 실행할 때의 동작 제어부.
    # - 자동 모드인 경우 둘 다 실행합니다.
    # - 그렇지 않으면 사용자에게 스트리밍 모드 여부를 물어 적절한 함수를 실행합니다.
    if is_auto_mode():
        asyncio.run(main())
        print()
        asyncio.run(main_stream())
    else:
        is_stream = input_with_fallback("Run in stream mode? (y/n): ", "n")
        if is_stream == "y":
            asyncio.run(main_stream())
        else:
            asyncio.run(main())
