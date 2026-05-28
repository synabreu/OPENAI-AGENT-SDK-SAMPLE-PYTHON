"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경을 활성화합니다(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성을 설치하거나 동기화합니다:
    make sync

3. 예제 실행:
    python examples/basic/remote_image.py

이 예제는 원격 이미지 URL을 에이전트에 전달해 이미지 내용을 질의하는 방법을 보여줍니다.
"""

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    """
    로컬 개발 환경 보조 함수.

    상위 디렉터리를 순회하여 `src/`, `.venv`의 site-packages, 그리고 `.env` 파일을
    찾아 `sys.path`와 환경변수를 설정합니다. 예제 파일을 로컬 저장소에서 바로
    실행할 수 있도록 도와줍니다.
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

URL = "https://images.unsplash.com/photo-1505761671935-60b3a7427bad?auto=format&fit=crop&w=400&q=80"


async def main():
    """
    메인 실행 함수.

    - `Agent` 인스턴스를 생성하고 원격 이미지 URL을 `input_image`로 전달합니다.
    - 에이전트를 실행하여 이미지에 대한 응답을 받고, 최종 출력을 콘솔에 출력합니다.
    """

    # 에이전트 생성: 간단한 어시스턴트 역할의 지침을 전달합니다.
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
    )

    # 에이전트 실행: 이미지 입력과 질문을 함께 전달합니다.
    result = await Runner.run(
        agent,
        [
            {
                "role": "user",
                "content": [{"type": "input_image", "detail": "auto", "image_url": URL}],
            },
            {
                "role": "user",
                "content": "What do you see in this image?",
            },
        ],
    )

    # 실행 결과의 최종 출력을 출력합니다.
    print(result.final_output)


if __name__ == "__main__":
    # 스크립트를 직접 실행할 때 메인 루틴을 실행합니다.
    # 예: `python examples/basic/remote_image.py`
    asyncio.run(main())
