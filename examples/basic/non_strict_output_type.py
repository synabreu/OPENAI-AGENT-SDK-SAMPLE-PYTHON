"""실행 방법 (터미널)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/non_strict_output_type.py

이 예제는 출력 스키마의 `strict_json_schema` 옵션을 시연합니다.
"""

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    # 로컬 개발 환경 보조: 상위 디렉터리를 순회하여 `src/`, `.venv`의
    # site-packages, 그리고 `.env` 파일을 찾아 `sys.path`와 환경변수를 설정합니다.
    # 예제를 로컬에서 쉽게 실행하려는 목적입니다.
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
import json
from dataclasses import dataclass
from typing import Any

from agents import Agent, AgentOutputSchema, AgentOutputSchemaBase, ModelBehaviorError, Runner

"""This example demonstrates how to use an output type that is not in strict mode. Strict mode
allows us to guarantee valid JSON output, but some schemas are not strict-compatible.

In this example, we define an output type that is not strict-compatible, and then we run the
agent with strict_json_schema=False.

We also demonstrate a custom output type.

To understand which schemas are strict-compatible, see:
https://platform.openai.com/docs/guides/structured-outputs?api-mode=responses#supported-schemas
"""


@dataclass
class OutputType:
    """
    간단한 출력 타입 예시.

    - `jokes`: 정수 인덱스를 키로 하고 문자열 농담을 값으로 갖는 딕셔너리.
    이 타입은 엄격한(strict) JSON 스키마와 호환되지 않을 수 있음을 보여줍니다.
    """
    jokes: dict[int, str]
    """농담 목록(번호별 인덱스)."""


class CustomOutputSchema(AgentOutputSchemaBase):
    """
    커스텀 출력 스키마 샘플.

    `AgentOutputSchemaBase`를 상속받아 커스텀 검증/파싱 로직을 구현합니다.
    이 예제는 모델이 반환한 JSON을 파싱해 리스트로 변환하는 동작을 보여줍니다.
    """

    def is_plain_text(self) -> bool:
        # 이 스키마는 플레인 텍스트가 아닌 구조화된 JSON을 기대합니다.
        return False

    def name(self) -> str:
        # 스키마 이름(디버깅/로그용)
        return "CustomOutputSchema"

    def json_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"jokes": {"type": "object", "properties": {"joke": {"type": "string"}}}},
        }

    def is_strict_json_schema(self) -> bool:
        # 엄격한 JSON 스키마를 지원하지 않음을 명시합니다.
        return False

    def validate_json(self, json_str: str) -> Any:
        json_obj = json.loads(json_str)
        # Just for demonstration, we'll return a list.
        # 간단한 데모: `jokes` 객체의 값들을 리스트로 변환해 반환합니다.
        return list(json_obj["jokes"].values())


async def main():
    """
    메인 실행 흐름.

    1) `OutputType`을 `output_type`으로 설정한 뒤 엄격 모드로 실행하면 예외가 발생할 수 있음을 보여줍니다.
    2) `AgentOutputSchema`를 사용해 `strict_json_schema=False`로 설정하면 비엄격 모드에서 파싱을 시도합니다.
    3) `CustomOutputSchema`를 사용해 커스텀 검증/파싱 로직을 시연합니다.
    """

    # 에이전트 생성: 기본 출력 타입으로 `OutputType`을 지정합니다.
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
        output_type=OutputType,
    )

    input = "Tell me 3 short jokes."

    # 1) 엄격 모드 시도: 이 출력 타입은 strict 호환이 아닐 수 있으므로 예외가 발생하는 것이 예상됩니다.
    try:
        result = await Runner.run(agent, input)
        raise AssertionError("Should have raised an exception")
    except Exception as e:
        print(f"Error (expected): {e}")

    # 2) 비엄격 모드로 재실행: `AgentOutputSchema`를 사용해 strict_json_schema=False로 설정합니다.
    agent.output_type = AgentOutputSchema(OutputType, strict_json_schema=False)
    try:
        result = await Runner.run(agent, input)
        print(result.final_output)
    except ModelBehaviorError as e:
        print(f"Non-strict output validation failed (expected possibility): {e}")

    # 3) 커스텀 출력 스키마를 사용해 파싱/검증 로직을 실행합니다.
    agent.output_type = CustomOutputSchema()
    result = await Runner.run(agent, input)
    print(result.final_output)


if __name__ == "__main__":
    # 스크립트를 직접 실행할 때 메인 루틴을 시작합니다.
    # 예: `python examples/basic/non_strict_output_type.py`
    asyncio.run(main())
