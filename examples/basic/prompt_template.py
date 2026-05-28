"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행(동적 프롬프트 사용 시):
    python examples/basic/prompt_template.py --dynamic --prompt-id <your_prompt_id>

4. 예제 실행(정적 프롬프트 사용 시):
    python examples/basic/prompt_template.py --prompt-id <your_prompt_id>

참고: 이 스크립트는 OpenAI 프롬프트 플레이그라운드에서 생성한 프롬프트 ID를 사용합니다.
"""

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    # 로컬 개발 환경 보조: 상위 디렉터리를 순회하며 `src/`, `.venv`의
    # site-packages, 그리고 `.env` 파일을 찾아 `sys.path`와 환경변수를 설정합니다.
    # 예제를 로컬에서 쉽게 실행하기 위한 유틸성 함수입니다.
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

import argparse
import asyncio
import random

from agents import Agent, GenerateDynamicPromptData, Runner

"""
참고: 이 예제는 기본 프롬프트 ID가 프로젝트에 없을 수 있으므로 바로 실행되지 않을 수 있습니다.

사용 방법:
1. https://platform.openai.com/playground/prompts 로 이동합니다.
2. `poem_style`라는 새 프롬프트 변수를 생성합니다.
3. 다음 내용을 가진 시스템 프롬프트를 생성합니다:
```
Write a poem in {{poem_style}}
```
4. `--prompt-id` 플래그를 사용하여 예제를 실행합니다.
"""

DEFAULT_PROMPT_ID = "pmpt_6965a984c7ac8194a8f4e79b00f838840118c1e58beb3332"


class DynamicContext:
    def __init__(self, prompt_id: str):
        # 동적 프롬프트 실행 시 사용할 컨텍스트를 보관합니다.
        # `prompt_id`는 플레이그라운드에서 생성한 프롬프트 식별자입니다.
        self.prompt_id = prompt_id
        # 예제용으로 시 스타일을 무작위로 선택합니다.
        self.poem_style = random.choice(["limerick", "haiku", "ballad"])
        print(f"[debug] DynamicContext initialized with poem_style: {self.poem_style}")


async def _get_dynamic_prompt(data: GenerateDynamicPromptData):
    # `GenerateDynamicPromptData`에서 전달된 컨텍스트를 읽어 동적으로
    # 프롬프트 정의를 생성합니다. 반환되는 딕셔너리는 Agent에 전달될
    # 프롬프트 사양(id, version, variables 등)을 포함해야 합니다.
    ctx: DynamicContext = data.context.context
    return {
        "id": ctx.prompt_id,
        "version": "1",
        "variables": {
            "poem_style": ctx.poem_style,
        },
    }


async def dynamic_prompt(prompt_id: str):
    """
    동적 프롬프트 예제 함수.

    - `DynamicContext`를 생성해 실행 컨텍스트를 준비합니다.
    - `Agent`를 생성할 때 `prompt`로 콜러블 `_get_dynamic_prompt`를 전달하면
      런타임에 프롬프트가 동적으로 생성되어 사용됩니다.
    """

    context = DynamicContext(prompt_id)

    agent = Agent(
        name="Assistant",
        prompt=_get_dynamic_prompt,
    )

    # 실제 실행: 질문과 함께 동적 컨텍스트를 전달합니다.
    result = await Runner.run(agent, "Tell me about recursion in programming.", context=context)
    print(result.final_output)


async def static_prompt(prompt_id: str):
    """
    정적 프롬프트 예제 함수.

    - `prompt`에 직접 프롬프트 사양을 전달해 고정된 변수를 사용합니다.
    """

    agent = Agent(
        name="Assistant",
        prompt={
            "id": prompt_id,
            "version": "1",
            "variables": {
                "poem_style": "limerick",
            },
        },
    )

    # 실행: 정적 프롬프트를 사용한 에이전트 실행
    result = await Runner.run(agent, "Tell me about recursion in programming.")
    print(result.final_output)


if __name__ == "__main__":
    # 커맨드라인 인터페이스: `--dynamic` 플래그로 동적 프롬프트를 사용하도록 전환할 수 있습니다.
    parser = argparse.ArgumentParser()
    parser.add_argument("--dynamic", action="store_true")
    parser.add_argument("--prompt-id", type=str, default=DEFAULT_PROMPT_ID)
    args = parser.parse_args()

    if args.dynamic:
        asyncio.run(dynamic_prompt(args.prompt_id))
    else:
        asyncio.run(static_prompt(args.prompt_id))
