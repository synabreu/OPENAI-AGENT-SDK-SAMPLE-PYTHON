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

"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/tools.py

이 예제는 간단한 도구(function tool)를 정의하고 에이전트를 통해 호출하는
방법을 보여줍니다. `Weather` Pydantic 모델을 사용해 함수의 반환 타입을
명시합니다.
"""

import asyncio
from typing import Annotated

from pydantic import BaseModel, Field

from agents import Agent, Runner, function_tool


class Weather(BaseModel):
    """날씨 정보를 담는 Pydantic 모델입니다.

    - `city`: 도시 이름
    - `temperature_range`: 섭씨 온도 범위(예: "14-20C")
    - `conditions`: 날씨 상태 설명
    """
    city: str = Field(description="The city name")
    temperature_range: str = Field(description="The temperature range in Celsius")
    conditions: str = Field(description="The weather conditions")


@function_tool
def get_weather(city: Annotated[str, "The city to get the weather for"]) -> Weather:
    """지정된 도시의 현재 날씨 정보를 반환하는 도구 함수입니다.

    반환값은 `Weather` 모델의 인스턴스입니다.
    """
    print("[debug] get_weather called")
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind.")


agent = Agent(
    name="Hello world",
    instructions="You are a helpful agent.",
    tools=[get_weather],
)


async def main():
    # 에이전트를 실행하여 도구를 호출하고 결과를 출력합니다.
    result = await Runner.run(agent, input="What's the weather in Seoul?")
    print(result.final_output)
    # 예시 출력: 도쿄의 날씨는 맑음(Sunny) 입니다.


if __name__ == "__main__":
    asyncio.run(main())
