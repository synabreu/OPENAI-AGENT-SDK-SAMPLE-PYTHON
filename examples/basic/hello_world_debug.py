"""Debug-friendly hello world example for the OpenAI Agents SDK.

이 파일은 이 저장소의 `examples/basic` 구조에 맞춘 디버깅 예제입니다.
직접 `OpenAI()` 클라이언트를 만드는 대신, 프로젝트의 핵심 흐름인
`Agent`와 `Runner.run()`을 사용합니다.

핵심 목표:
1. Agents SDK 방식으로 가장 작은 hello world 에이전트를 실행한다.
2. `RunResult.raw_responses`에서 response id와 request id를 출력한다.
3. 실행 실패 시 로컬 로그만 보고도 인증, 네트워크, API 오류를 구분하기 쉽게 한다.

실행 전 준비:
    export OPENAI_API_KEY="sk-..."

실행:
    python examples/basic/hello_world_debug.py
"""

from __future__ import annotations

import asyncio
import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    """로컬 예제 실행을 위한 저장소 환경을 구성합니다.

    이 프로젝트의 basic 예제들은 로컬 checkout 상태에서도 바로 실행할 수 있도록
    비슷한 형태의 환경 로딩 함수를 사용합니다.

    동작:
    1. 현재 파일의 상위 디렉터리를 올라가며 `src/`가 있는 프로젝트 루트를 찾습니다.
    2. 프로젝트 루트와 `src/`를 `sys.path` 앞쪽에 추가해 로컬 Agents SDK 코드를
       import하도록 합니다.
    3. `.venv`가 있으면 해당 가상환경의 `site-packages`를 추가합니다.
    4. `.env`가 있으면 `KEY=VALUE` 형식으로 환경 변수를 로드합니다.

    이미 존재하는 환경 변수는 덮어쓰지 않으므로, 셸에서 지정한 값이 우선합니다.
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

    Agents SDK는 내부적으로 OpenAI 모델 provider를 호출하므로 API 키가 필요합니다.
    키가 없을 때 SDK 내부에서 실패하도록 두기보다, 예제 시작 지점에서
    명확한 메시지를 보여주면 디버깅이 빨라집니다.
    """

    if not _os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            'Set it first, for example: export OPENAI_API_KEY="sk-..."'
        )


# 이 저장소의 다른 basic 예제들과 동일하게, 로컬 `src/`와 `.env`를 먼저 로드합니다.
_load_repo_env()

from agents import Agent, Runner, RunResult


def print_model_debug_info(result: RunResult) -> None:
    """Agents SDK 실행 결과에서 모델 호출 디버깅 정보를 출력합니다.

    Args:
        result: `Runner.run()`이 반환한 실행 결과입니다.

    Debugging notes:
        - `result.last_response_id`는 마지막 모델 응답 id입니다.
        - `result.raw_responses`에는 실행 중 발생한 LLM 응답들이 순서대로 들어 있습니다.
        - 각 raw response의 `request_id`는 OpenAI API의 transport request id입니다.
          장애 분석이나 지원 문의 시 가장 중요한 값입니다.
    """

    print("\n=== Debug info ===")
    print("last_response_id:", result.last_response_id)
    print("raw_response_count:", len(result.raw_responses))

    for index, response in enumerate(result.raw_responses, start=1):
        print(f"raw_response[{index}].response_id:", response.response_id)
        print(f"raw_response[{index}].request_id:", response.request_id)
        print(f"raw_response[{index}].input_tokens:", response.usage.input_tokens)
        print(f"raw_response[{index}].output_tokens:", response.usage.output_tokens)
        print(f"raw_response[{index}].total_tokens:", response.usage.total_tokens)


async def run_hello_world() -> RunResult:
    """디버깅 정보를 확인하기 쉬운 hello world 에이전트를 실행합니다.

    Returns:
        Agents SDK의 `RunResult` 객체입니다.

    이 함수는 프로젝트 아키텍처에 맞게 `Agent`를 만들고 `Runner.run()`으로
    실행합니다. `OPENAI_MODEL` 환경 변수가 있으면 해당 모델을 명시적으로 사용하고,
    없으면 Agents SDK의 기본 모델 설정을 그대로 사용합니다.
    """

    _require_api_key()

    model = _os.getenv("OPENAI_MODEL")

    agent = Agent(
        name="Debug Assistant",
        instructions="You are a concise assistant. Answer in Korean with one short sentence.",
        **({"model": model} if model else {}),
    )

    if model:
        print(f"Running Agents SDK hello world with model={model!r}")
    else:
        print("Running Agents SDK hello world with the SDK default model")

    return await Runner.run(
        agent,
        "Say hello and mention this is a debug run.",
    )


async def main() -> None:
    """비동기 스크립트 진입점입니다.

    `Runner.run()`은 비동기 API이므로 `asyncio.run(main())`으로 실행합니다.
    성공하면 최종 응답과 모델 호출 메타데이터를 출력합니다. 실패하면 어떤 단계에서
    문제가 났는지 볼 수 있도록 예외 타입과 메시지를 출력한 뒤 다시 raise합니다.
    """

    try:
        result = await run_hello_world()
        print("\n=== Final output ===")
        print(result.final_output)
        print_model_debug_info(result)

    except Exception as exc:
        # 예제 파일에서는 오류를 삼키지 않고 다시 raise합니다.
        # 이렇게 해야 터미널에서 전체 traceback을 확인할 수 있어 원인 파악이 쉽습니다.
        print("\n=== Run failed ===")
        print("error_type:", exc.__class__.__name__)
        print("error:", exc)
        raise


if __name__ == "__main__":
    asyncio.run(main())
