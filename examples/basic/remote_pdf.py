"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/remote_pdf.py

이 예제는 원격 PDF 파일(URL)을 에이전트에 전달해 요약을 요청하는 방법을 보여줍니다.
"""

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    """
    로컬 개발 환경 보조 함수.

    상위 디렉터리를 순회하여 `src/`, `.venv`의 site-packages, 그리고 `.env` 파일을
    찾아 `sys.path`와 환경변수를 설정합니다. 예제를 로컬 저장소에서 바로
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

URL = "https://www.berkshirehathaway.com/letters/2024ltr.pdf"


async def main():
    """
    메인 실행 함수.

    - 에이전트 인스턴스를 생성하고 원격 PDF의 URL을 `input_file`로 전달합니다.
    - 에이전트를 실행해 문서를 요약하도록 요청하고 최종 출력을 출력합니다.
    """

    # 에이전트 생성: 간단한 어시스턴트 역할 지침을 지정합니다.
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
    )

    # 에이전트 실행: 파일 URL과 질문을 함께 전달하여 요약을 요청합니다.
    result = await Runner.run(
        agent,
        [
            {
                "role": "user",
                "content": [{"type": "input_file", "file_url": URL}],
            },
            {
                "role": "user",
                "content": "Can you summarize the letter?",
            },
        ],
    )

    # 실행 결과의 최종 출력을 출력합니다.
    print(result.final_output)


if __name__ == "__main__":
    # 스크립트를 직접 실행할 때 메인 루틴을 시작합니다.
    # 예: `python examples/basic/remote_pdf.py`
    asyncio.run(main())
