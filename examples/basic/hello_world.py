import asyncio

import os as _os
import sys as _sys
from pathlib import Path as _Path


"""Simple example agent runner.

이 모듈은 레포지토리 예제 중 하나로, 로컬 개발환경에서 예제를
직접 실행할 때 필요한 경로 설정과 간단한 `Agent` 실행 흐름을 보여줍니다.

주요 기능:
- `_load_repo_env()` : 로컬 `src/`와 `.venv`의 `site-packages`를
  `sys.path`에 추가하여 로컬 패키지와 가상환경 종속성을 사용할 수
  있도록 합니다. 또한 상위 디렉터리의 `.env` 파일이 있으면 환경변수를
  로드합니다.
- `main()` : `Agent`를 생성하고 `Runner.run()`을 통해 에이전트를 실행,
  결과의 `final_output`을 콘솔에 출력합니다.

모든 주석은 이해를 돕기 위해 한국어로 작성되어 있습니다.
"""


def _load_repo_env() -> None:
    """로컬 개발 환경을 구성합니다.

    동작 요약:
    1. 현재 파일의 상위 디렉터리들을 검색합니다.
    2. 각 디렉터리에 `src/`가 있으면 그 경로와 프로젝트 루트를
       `sys.path`의 앞부분에 삽입해 로컬 패키지가 우선적으로 import
       되도록 합니다.
    3. `.venv`가 있으면 해당 가상환경의 `site-packages`를 찾아 `sys.path`
       에 추가합니다. (이미 `src/`가 추가되었다면 그 뒤에 삽입)
    4. `.env` 파일이 있으면 `KEY=VALUE` 형식으로 읽어 `os.environ`에
       기본값으로 설정합니다. 주석이나 빈 라인은 무시합니다.

    이 함수는 예제 파일을 로컬에서 실행할 때 경로 문제로 인한 import
    실패를 방지하기 위한 보조 로직입니다. `.env`는 첫 번째로 발견된
    파일만 적용하며 적용 후 함수를 종료합니다.
    """

    for _directory in _Path(__file__).resolve().parents:
        # 로컬 소스 디렉터리(src/)가 있으면 우선적으로 경로에 추가
        _src_path = _directory / "src"
        if _src_path.exists():
            _root = str(_directory)
            if _root not in _sys.path:
                # 프로젝트 루트를 최우선으로 삽입
                _sys.path.insert(0, _root)
            _src = str(_src_path)
            if _src not in _sys.path:
                _sys.path.insert(0, _src)

        # 가상환경(.venv)이 있으면 그 안의 site-packages를 찾아 추가
        _venv_path = _directory / ".venv"
        if _venv_path.exists():
            _site_packages = next(_venv_path.glob("lib/python*/site-packages"), None)
            if _site_packages is not None:
                _site = str(_site_packages)
                if _site not in _sys.path:
                    # src가 이미 추가되어 있다면 그 다음 위치에 삽입
                    _sys.path.insert(1 if _src_path.exists() else 0, _site)

        # .env 파일이 있으면 간단한 KEY=VALUE 형식으로 환경변수를 로드
        _env_path = _directory / ".env"
        if not _env_path.exists():
            continue

        for _line in _env_path.read_text().splitlines():
            _line = _line.strip()
            # 빈 줄, 주석(#), 혹은 '='이 없는 라인은 무시
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _value = _line.split("=", 1)
            # 이미 존재하는 환경변수는 덮어쓰지 않고 기본값으로 설정
            _os.environ.setdefault(_key.strip(), _value.strip().strip("\"'"))
        # 첫 번째로 발견된 .env만 적용하고 함수 종료
        return


# 예제를 로컬에서 바로 실행할 때 로컬 src/와 .venv의 site-packages를
# 사용할 수 있도록 시작 시점에 환경을 정비합니다.
_load_repo_env()

from agents import Agent, Runner


async def main():
    """함수 진입점

    - `Agent`를 생성할 때 `name`과 `instructions`를 전달합니다.
      이 예제에서는 에이전트가 하이쿠(3행 시 형태)로만 응답하도록
      간단히 지시합니다.
    - `Runner.run(agent, input)`을 호출하여 에이전트를 실행하고
      반환된 결과에서 `final_output`을 출력합니다.

    실제 사용 시에는 에이전트에 도구(tool), 메모리, 커스텀 훅 등
    다양한 설정을 추가할 수 있습니다. 이 예제는 최소 동작만을
    보여주기 위한 목적입니다.
    """

    agent = Agent(
        name="Assistant",
        instructions="You only respond in haikus.",
    )

    # Runner.run은 에이전트를 호출하여 모델이 생성한 응답을 담은
    # 결과 객체를 반환합니다. 여기서는 단순히 문자열 입력을 전달.
    result = await Runner.run(agent, "Tell me about recursion in programming.")
    # 최종 출력(모델이 생성한 텍스트)을 출력합니다.
    print(result.final_output)
    # 참고용 문장 (실제 출력은 모델에 따라 달라집니다):
    # Function calls itself,
    # Looping in smaller pieces,
    # Endless by design.


if __name__ == "__main__":
    # 파이썬 스크립트로 직접 실행할 때 비동기 메인 루프를 실행
    asyncio.run(main())
