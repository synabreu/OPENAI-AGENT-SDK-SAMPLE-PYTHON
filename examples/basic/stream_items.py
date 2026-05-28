"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/stream_items.py

이 예제는 스트리밍 런(streamed run)을 통해 에이전트의 아이템(item)
이벤트(예: 도구 호출, 도구 출력, 메시지 출력)를 실시간으로 처리하는 방법을
보여줍니다.
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
import random

from agents import Agent, ItemHelpers, Runner, function_tool


@function_tool
def how_many_jokes() -> int:
    """몇 개의 농담을 할지 무작위로 정하는 도구 함수입니다.

    1에서 10 사이의 정수를 반환합니다(양끝 포함).
    """
    return random.randint(1, 10)


async def main():
    # 에이전트와 도구 설정
    agent = Agent(
        name="Joker",
        instructions="First call the `how_many_jokes` tool, then tell that many jokes.",
        tools=[how_many_jokes],
    )

    result = Runner.run_streamed(
        agent,
        input="Hello",
    )
    print("=== Run starting ===")
    async for event in result.stream_events():
        # raw_response_event 델타는 무시합니다(원시 응답 스트림의 내부 델타).
        if event.type == "raw_response_event":
            continue
        # 에이전트가 업데이트되었을 때(예: 에이전트 설정이 바뀐 경우)
        elif event.type == "agent_updated_stream_event":
            print(f"Agent updated: {event.new_agent.name}")
            continue
        # 런 아이템 이벤트 처리: 도구 호출, 도구 출력, 메시지 출력 등
        elif event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                print(f"-- Tool was called: {getattr(event.item.raw_item, 'name', 'Unknown Tool')}")
            elif event.item.type == "tool_call_output_item":
                print(f"-- Tool output: {event.item.output}")
            elif event.item.type == "message_output_item":
                print(f"-- Message output:\n {ItemHelpers.text_message_output(event.item)}")
            else:
                pass  # 다른 이벤트 타입은 무시

    print("=== Run complete ===")


if __name__ == "__main__":
    asyncio.run(main())

    # === Run starting ===
    # Agent updated: Joker
    # -- Tool was called: how_many_jokes
    # -- Tool output: 4
    # -- Message output:
    #  Sure, here are four jokes for you:

    # 1. **Why don't skeletons fight each other?**
    #    They don't have the guts!

    # 2. **What do you call fake spaghetti?**
    #    An impasta!

    # 3. **Why did the scarecrow win an award?**
    #    Because he was outstanding in his field!

    # 4. **Why did the bicycle fall over?**
    #    Because it was two-tired!
    # === Run complete ===
