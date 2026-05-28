"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/stream_function_call_args.py

이 예제는 함수 호출 인수(function call arguments)가 실시간으로 스트리밍되어
전달되는 방식을 시연합니다. 인수는 점진적으로 생성되며, 그 과정에서 화면에
즉시 출력되어 어떤 인자가 만들어지는지 확인할 수 있습니다.
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
from typing import Annotated, Any

from openai.types.responses import ResponseFunctionCallArgumentsDeltaEvent

from agents import Agent, Runner, function_tool


@function_tool
def write_file(filename: Annotated[str, "Name of the file"], content: str) -> str:
    """파일에 내용을 쓰는 도구 함수입니다.

    - `filename`: 생성할 파일명
    - `content`: 파일에 쓸 문자열 내용
    성공하면 성공 메시지 문자열을 반환합니다.
    """
    return f"File {filename} written successfully"


@function_tool
def create_config(
    project_name: Annotated[str, "Project name"],
    version: Annotated[str, "Project version"],
    dependencies: Annotated[list[str] | None, "Dependencies (list of packages)"],
) -> str:
    """프로젝트 구성(configuration) 파일을 생성하는 도구 함수입니다.

    - `project_name`: 프로젝트 이름
    - `version`: 프로젝트 버전 문자열
    - `dependencies`: 패키지 의존성 리스트(없을 수 있음)
    성공하면 생성된 구성 정보를 요약한 문자열을 반환합니다.
    """
    return f"Config for {project_name} v{version} created"


async def main():
    """함수 호출 인수의 실시간 스트리밍을 시연하는 메인 함수입니다.

    인수는 생성되는 즉시 델타(delta) 단위로 스트리밍되어 출력됩니다.
    이 동작은 파라미터 생성 과정에서 즉각적인 피드백을 제공하는 데 유용합니다.
    """
    agent = Agent(
        name="CodeGenerator",
        instructions="You are a helpful coding assistant. Use the provided tools to create files and configurations.",
        tools=[write_file, create_config],
    )

    print("🚀 Function Call Arguments Streaming Demo")

    result = Runner.run_streamed(
        agent,
        input="Create a Python web project called 'my-app' with FastAPI. Version 1.0.0, dependencies: fastapi, uvicorn",
    )

    # 상세 출력을 위해 함수 호출을 추적합니다.
    # 구조: call_id -> {name, arguments}
    function_calls: dict[Any, dict[str, Any]] = {}
    current_active_call_id = None

    async for event in result.stream_events():
        if event.type == "raw_response_event":
            # 함수 호출이 새로 추가되었음을 감지합니다.
            if event.data.type == "response.output_item.added":
                if getattr(event.data.item, "type", None) == "function_call":
                    function_name = getattr(event.data.item, "name", "unknown")
                    call_id = getattr(event.data.item, "call_id", "unknown")

                    # 새로운 호출 정보를 초기화합니다.
                    function_calls[call_id] = {"name": function_name, "arguments": ""}
                    current_active_call_id = call_id
                    print(f"\n📞 Function call streaming started: {function_name}()")
                    print("📝 Arguments building...")

            # 인수 델타가 도착하면 현재 활성 호출에 누적합니다.
            elif isinstance(event.data, ResponseFunctionCallArgumentsDeltaEvent):
                if current_active_call_id and current_active_call_id in function_calls:
                    function_calls[current_active_call_id]["arguments"] += event.data.delta
                    print(event.data.delta, end="", flush=True)

            # 함수 호출이 완료되었을 때의 처리입니다.
            elif event.data.type == "response.output_item.done":
                if hasattr(event.data.item, "call_id"):
                    call_id = getattr(event.data.item, "call_id", "unknown")
                    if call_id in function_calls:
                        function_info = function_calls[call_id]
                        print(f"\n✅ Function call streaming completed: {function_info['name']}")
                        print()
                        if current_active_call_id == call_id:
                            current_active_call_id = None

    print("Summary of all function calls:")
    for call_id, info in function_calls.items():
        print(f"  - #{call_id}: {info['name']}({info['arguments']})")

    print(f"\nResult: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
