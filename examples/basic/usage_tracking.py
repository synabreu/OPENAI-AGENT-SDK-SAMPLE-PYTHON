"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/usage_tracking.py

이 예제는 실행 결과의 사용량(usage) 정보를 조회하는 방법을 보여줍니다.
`Usage` 객체에서 토큰 수 및 요청별 사용량을 출력합니다.
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

import asyncio

from pydantic import BaseModel

from agents import Agent, Runner, Usage, function_tool


class Weather(BaseModel):
    """날씨 정보를 담는 Pydantic 모델입니다.

    - `city`: 도시 이름
    - `temperature_range`: 섭씨 온도 범위
    - `conditions`: 날씨 상태 설명
    """
    city: str
    temperature_range: str
    conditions: str


@function_tool
def get_weather(city: str) -> Weather:
    """지정된 도시의 현재 날씨 정보를 반환하는 도구 함수입니다.

    반환값은 `Weather` 모델 인스턴스입니다.
    """
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind.")


def print_usage(usage: Usage) -> None:
    """`Usage` 객체의 항목들을 사람이 읽기 쉬운 형태로 출력합니다.

    - 전체 입력/출력/총 토큰 수 및 요청 수를 출력합니다.
    - 각 요청(request)별 입력/출력 토큰도 나열합니다.
    """
    print("\n=== Usage ===")
    print(f"Input tokens: {usage.input_tokens}")
    print(f"Output tokens: {usage.output_tokens}")
    print(f"Total tokens: {usage.total_tokens}")
    print(f"Requests: {usage.requests}")
    for i, request in enumerate(usage.request_usage_entries):
        print(f"  {i + 1}: {request.input_tokens} input, {request.output_tokens} output")


async def main() -> None:
    # 에이전트 설정: 간단한 지시문과 `get_weather` 도구를 사용합니다.
    agent = Agent(
        name="Usage Demo",
        instructions="You are a concise assistant. Use tools if needed.",
        tools=[get_weather],
    )

    # 에이전트를 실행하고 결과와 사용량 정보를 출력합니다.
    result = await Runner.run(agent, "What's the weather in Tokyo?")

    print("\nFinal output:")
    print(result.final_output)

    # 실행 컨텍스트에서 Usage 정보를 조회하여 출력합니다.
    print_usage(result.context_wrapper.usage)


if __name__ == "__main__":
    asyncio.run(main())
