# 실행 방법 (터미널)
# 1. (선택) 프로젝트의 가상환경을 활성화합니다(포함된 .venv 사용 시):
#    source .venv/bin/activate
# 2. (선택) 의존성을 설치하거나 동기화합니다:
#    make sync
# 3. 예제 실행:
#    python examples/basic/local_image.py
# 4. 프로젝트에 `uv` 실행기가 설정되어 있으면 다음처럼 실행할 수 있습니다:
#    uv run python examples/basic/local_image.py
# 참고: 이 스크립트는 `examples/basic/media/image_bison.jpg` 파일을 사용합니다.

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

FILEPATH = os.path.join(os.path.dirname(__file__), "media/image_bison.jpg")


def image_to_base64(image_path):
    """
    이미지 파일을 읽어 base64로 인코딩한 문자열을 반환합니다.

    반환 값은 UTF-8로 디코딩된 base64 문자열입니다. 에이전트에
    `data:image/...;base64,` 형태로 전달할 때 사용합니다.
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


async def main():
    """
    메인 실행 함수.

    - 로컬 이미지를 base64로 인코딩합니다.
    - `Agent` 인스턴스를 생성하고 이미지 입력(`input_image`)과 질문을 함께 전달해 실행합니다.
    - 실행 결과의 최종 출력을 콘솔에 출력합니다.
    """

    # 로컬 이미지를 base64로 변환합니다.
    b64_image = image_to_base64(FILEPATH)

    # 에이전트 인스턴스 생성: 모델에 전달할 간단한 지침을 설정합니다.
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
    )

    # 에이전트 실행: 이미지 입력과 질문을 전달합니다.
    result = await Runner.run(
        agent,
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "detail": "auto",
                        "image_url": f"data:image/jpeg;base64,{b64_image}",
                    }
                ],
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
    # 예: `python examples/basic/local_image.py`
    asyncio.run(main())
