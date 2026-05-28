"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/stream_text.py

이 예제는 스트리밍 텍스트 델타(ResponseTextDeltaEvent)를 구독하여
모델이 생성하는 텍스트를 실시간으로 출력하는 간단한 데모입니다.
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

from openai.types.responses import ResponseTextDeltaEvent

from agents import Agent, Runner


async def main():
    # 에이전트 초기화: 간단한 지시문을 사용합니다.
    agent = Agent(
        name="Joker",
        instructions="You are a helpful assistant.",
    )

    # 스트리밍 실행: 모델이 생성하는 텍스트 델타를 실시간으로 수신합니다.
    result = Runner.run_streamed(agent, input="Please tell me 5 jokes.")
    async for event in result.stream_events():
        # ResponseTextDeltaEvent 타입의 델타를 수신하면 즉시 출력합니다.
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
