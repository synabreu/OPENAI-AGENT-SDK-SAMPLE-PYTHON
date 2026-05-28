# 실행 방법 (터미널)
# 1. (선택) 프로젝트의 가상환경을 활성화합니다(포함된 .venv 사용 시):
#    source .venv/bin/activate
# 2. (선택) 의존성을 설치하거나 동기화합니다:
#    make sync
# 3. 예제 실행:
#    python examples/basic/local_file.py
# 4. 프로젝트에 `uv` 실행기가 설정되어 있으면 다음처럼 실행할 수 있습니다:
#    uv run python examples/basic/local_file.py
# 참고: 예제는 `examples/basic/media/` 폴더의 PDF 파일을 사용합니다.

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    # 로컬 개발 환경 보조: 상위 디렉터리를 순회하여 `src/`, `.venv`의
    # site-packages, 그리고 `.env` 파일을 찾아 `sys.path`와 환경변수를 설정합니다.
    # 이 함수는 예제 실행이 로컬 저장소 환경에서 올바르게 동작하도록 도와줍니다.
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
import base64
import os

from agents import Agent, Runner

FILEPATH = os.path.join(os.path.dirname(__file__), "media/partial_o3-and-o4-mini-system-card.pdf")


def file_to_base64(file_path: str) -> str:
    """
    파일 경로(`file_path`)를 읽어 base64로 인코딩한 문자열을 반환합니다.

    반환 형식은 UTF-8로 디코딩된 base64 문자열입니다. 주로 에이전트에
    파일을 `data:...;base64,` 형태로 전달할 때 사용됩니다.
    """
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def main():
    """
    메인 실행 함수.

    - `Agent` 인스턴스를 생성합니다(여기서는 간단한 어시스턴트 역할).
    - 로컬 PDF 파일을 base64로 인코딩하여 에이전트 입력(`input_file`)으로 전달합니다.
    - `Runner.run`을 호출해 에이전트를 실행하고 응답의 최종 출력을 출력합니다.
    """

    # 에이전트 인스턴스 생성: 모델에 전달할 지침을 지정합니다.
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
    )

    # 로컬 파일을 base64로 변환하여 에이전트에 전달할 준비를 합니다.
    b64_file = file_to_base64(FILEPATH)

    # 에이전트 실행: 파일 입력과 질문을 함께 전달합니다.
    result = await Runner.run(
        agent,
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_data": f"data:application/pdf;base64,{b64_file}",
                        "filename": "partial_o3-and-o4-mini-system-card.pdf",
                    }
                ],
            },
            {
                "role": "user",
                "content": "What is the first sentence of the introduction?",
            },
        ],
    )

    # 실행 결과의 최종 출력값을 콘솔에 출력합니다.
    print(result.final_output)


if __name__ == "__main__":
    # 스크립트를 직접 실행할 때 메인 루틴을 실행합니다.
    # 예: `python examples/basic/local_file.py`
    asyncio.run(main())
