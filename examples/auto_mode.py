"""예제 자동 실행을 위한 유틸리티들.

환경 변수 `EXAMPLES_INTERACTIVE_MODE=auto`가 설정되면, 이 헬퍼들은
결정론적 입력과 확인 동작을 제공하여 예제를 수동 상호작용 없이 자동으로
실행할 수 있게 합니다. 이 헬퍼들은 예제 코드에 의존성을 추가하지 않도록
의도적으로 가볍게 설계되어 있습니다.

실행 방법 (터미널 예시):
1. 가상환경 활성화(선택):
    source .venv/bin/activate
2. 필요 시 의존성 설치/동기화:
    make sync
3. 예제 실행(예: 자동 모드로 실행하려면 환경 변수 설정):
    EXAMPLES_INTERACTIVE_MODE=auto python examples/auto_mode.py
    또는 일반 실행:
    python examples/auto_mode.py
"""

from __future__ import annotations

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


import os


def is_auto_mode() -> bool:
    """예제가 대화형 프롬프트를 건너뛰고 자동 모드로 실행되어야 하면 True를 반환합니다."""
    # 환경 변수 `EXAMPLES_INTERACTIVE_MODE`를 확인하여 자동 모드 여부를 결정합니다.
    # 값이 'auto'로 설정되어 있으면 예제는 상호작용 프롬프트를 건너뜁니다.
    return os.environ.get("EXAMPLES_INTERACTIVE_MODE", "").lower() == "auto"


def input_with_fallback(prompt: str, fallback: str) -> str:
    """자동 모드면 `fallback` 문자열을 반환하고, 그렇지 않으면 `input()`을 호출합니다."""
    if is_auto_mode():
        # 자동 모드일 경우, 사용자를 묻지 않고 대체값을 사용합니다.
        # 또한 어떤 프롬프트에 대해 어떤 대체값을 사용했는지 로그로 출력합니다.
        print(f"[auto-input] {prompt.strip()} -> {fallback}")
        return fallback

    # 수동 모드일 경우 실제로 사용자에게 입력을 요청합니다.
    return input(prompt)


def confirm_with_fallback(prompt: str, default: bool = True) -> bool:
    """자동 모드면 기본값(`default`)을 반환하고, 그렇지 않으면 사용자에게 확인을 요청합니다."""
    if is_auto_mode():
        # 자동 모드에서는 사용자 확인을 건너뛰고 기본값을 선택한 것으로 처리합니다.
        choice = "yes" if default else "no"
        print(f"[auto-confirm] {prompt.strip()} -> {choice}")
        return default

    # 수동 모드: 사용자의 응답을 읽고 빈 응답이면 기본값을 사용합니다.
    answer = input(prompt).strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}
