"""Image tool output example.

이 예제는 Agents SDK의 function tool이 이미지 output을 반환하고,
모델이 그 이미지를 보고 최종 설명을 생성하는 흐름을 보여줍니다.

실행 전 준비:
    export OPENAI_API_KEY="sk-..."

실행 위치:
    OPENAI-AGENT-SDK-SAMPLE-PYTHON 프로젝트 루트

실행:
    python examples/basic/image_tool_output.py

확인할 점:
    - 터미널에 "Image tool called"가 출력되면 모델이 tool을 호출한 것입니다.
    - 마지막 출력은 tool의 raw 반환값이 아니라, 이미지를 본 모델의 최종 설명입니다.
    - `return_typed_dict` 값을 False로 바꾸면 dict 대신 `ToolOutputImage` 타입으로
      같은 이미지 output을 반환하는 방식을 확인할 수 있습니다.
"""

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    """로컬 checkout 상태에서 예제를 바로 실행할 수 있도록 환경을 구성합니다.

    이 저장소의 basic 예제들은 `src/agents` 패키지를 editable install 하지 않아도
    실행될 수 있게 비슷한 부트스트랩 코드를 포함합니다.

    동작:
    1. 현재 파일의 상위 디렉터리들을 차례로 확인합니다.
    2. `src/` 폴더가 있는 디렉터리를 프로젝트 루트로 보고, 루트와 `src/`를
       `sys.path` 앞쪽에 추가합니다. 이렇게 하면 pip로 설치된 패키지보다
       현재 작업 중인 로컬 SDK 코드가 먼저 import됩니다.
    3. `.venv`가 있으면 해당 가상환경의 `site-packages`를 찾아 추가합니다.
    4. `.env`가 있으면 `KEY=VALUE` 형식의 환경 변수를 읽어옵니다.

    이미 셸에 설정된 환경 변수는 덮어쓰지 않습니다. 예를 들어 터미널에서
    `OPENAI_API_KEY`를 따로 지정했다면 `.env` 값보다 그 값이 우선합니다.
    """

    for _directory in _Path(__file__).resolve().parents:
        # 프로젝트 루트에는 `src/`가 있습니다. 찾으면 현재 로컬 패키지를
        # 우선 import할 수 있도록 프로젝트 루트와 `src/`를 sys.path에 넣습니다.
        _src_path = _directory / "src"
        if _src_path.exists():
            _root = str(_directory)
            if _root not in _sys.path:
                _sys.path.insert(0, _root)
            _src = str(_src_path)
            if _src not in _sys.path:
                _sys.path.insert(0, _src)

        # 로컬 가상환경이 있으면 그 안의 site-packages도 import 경로에 추가합니다.
        # 예제 파일을 `python examples/basic/...`처럼 직접 실행할 때 유용합니다.
        _venv_path = _directory / ".venv"
        if _venv_path.exists():
            _site_packages = next(_venv_path.glob("lib/python*/site-packages"), None)
            if _site_packages is not None:
                _site = str(_site_packages)
                if _site not in _sys.path:
                    _sys.path.insert(1 if _src_path.exists() else 0, _site)

        # `.env` 파일을 찾으면 간단한 KEY=VALUE 라인만 읽습니다.
        # 주석, 빈 줄, '='가 없는 라인은 무시합니다.
        _env_path = _directory / ".env"
        if not _env_path.exists():
            continue

        for _line in _env_path.read_text().splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _value = _line.split("=", 1)
            _os.environ.setdefault(_key.strip(), _value.strip().strip("\"'"))
        # 가장 가까운 프로젝트 `.env` 하나만 읽고 종료합니다.
        return


# Agents SDK를 import하기 전에 로컬 개발환경을 먼저 정비합니다.
_load_repo_env()

import asyncio

from agents import Agent, Runner, ToolOutputImage, ToolOutputImageDict, function_tool

# 이 플래그는 같은 이미지 tool output을 두 가지 방식으로 반환할 수 있음을 보여줍니다.
# True이면 plain dict 형태(`ToolOutputImageDict`)로 반환하고,
# False이면 SDK dataclass 형태(`ToolOutputImage`)로 반환합니다.
return_typed_dict = True

# 예제에서 tool이 반환할 이미지 URL입니다.
# Unsplash의 공개 이미지 URL을 사용하며, 모델은 이 이미지를 받아서 설명합니다.
URL = "https://images.unsplash.com/photo-1505761671935-60b3a7427bad?auto=format&fit=crop&w=400&q=80"


@function_tool
def fetch_random_image() -> ToolOutputImage | ToolOutputImageDict:
    """이미지 tool output을 반환합니다.

    `@function_tool` 데코레이터는 이 파이썬 함수를 Agent가 호출할 수 있는
    도구로 등록합니다. 모델이 사용자 요청을 보고 이미지가 필요하다고 판단하면
    이 tool을 호출하고, 반환된 image output을 다시 모델 입력으로 사용합니다.

    Returns:
        `ToolOutputImageDict` 또는 `ToolOutputImage`입니다. 두 형태 모두
        Agents SDK가 이미지 tool output으로 이해할 수 있습니다.

    반환 필드:
        - `type`: dict 반환 시 이것이 이미지 output임을 나타냅니다.
        - `image_url`: 모델이 볼 이미지의 URL입니다.
        - `detail`: 이미지 해석 상세도를 지정합니다. `"auto"`는 SDK/모델이
          적절한 상세도를 선택하게 합니다.
    """

    print("Image tool called")

    # dict 기반 반환은 JSON-like 구조를 직접 확인하기 쉬워 예제나 디버깅에 편합니다.
    if return_typed_dict:
        return {"type": "image", "image_url": URL, "detail": "auto"}

    # SDK 타입 기반 반환은 타입 힌트와 IDE 자동완성의 도움을 받기 좋습니다.
    return ToolOutputImage(image_url=URL, detail="auto")


async def main():
    """이미지 tool을 가진 Agent를 실행합니다.

    흐름:
    1. `fetch_random_image` tool을 가진 Agent를 생성합니다.
    2. 사용자 입력으로 tool 사용과 이미지 설명을 요청합니다.
    3. Runner가 모델을 실행하고, 필요하면 tool을 호출한 뒤 최종 답변을 만듭니다.
    4. `result.final_output`에 들어 있는 최종 텍스트를 출력합니다.
    """

    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
        tools=[fetch_random_image],
    )

    # Runner.run은 Agent 실행 루프를 처리합니다.
    # 이 요청에서는 모델이 이미지가 필요하다고 판단하면 `fetch_random_image`를 호출하고,
    # tool이 반환한 이미지 URL을 근거로 이미지를 설명하는 최종 답변을 생성합니다.
    result = await Runner.run(
        agent,
        input="Fetch an image using the random_image tool, then describe it",
    )

    # 최종 출력은 tool 호출 결과 자체가 아니라, tool 결과를 본 모델의 답변입니다.
    print(result.final_output)
    """This image features the famous clock tower, commonly known as Big Ben, ..."""


if __name__ == "__main__":
    # 이 예제는 비동기 Runner API를 사용하므로 asyncio.run으로 main을 실행합니다.
    asyncio.run(main())
