"""Examples 패키지 초기화.

이 파일은 `examples` 디렉터리를 패키지로 만들어 최상위 모듈 이름 충돌을
방지합니다. 예를 들어 `examples/customer_service/main.py`와
`examples/researcher_app/main.py`는 각각 별개의 모듈으로 취급됩니다.

실행 방법(터미널 예시):
1. 가상환경 활성화(선택):
    source .venv/bin/activate
2. 의존성 설치/동기화(선택):
    make sync
3. 예제 파일을 실행하려면, 예를 들어:
    python examples/basic/tools.py

이 파일 내부의 `_load_repo_env()`는 예제에서 로컬 `src/`와 `.venv`를
자동으로 경로에 추가하여 개발 환경에서 바로 예제를 실행할 수 있게
도와주는 유틸리티입니다.
"""

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _load_repo_env() -> None:
    """레포지토리 루트의 `src/`, `.venv` 및 `.env`를 자동으로 로드합니다.

    - `src/`가 있으면 `sys.path`에 추가하여 로컬 패키지 임포트가 작동하게 합니다.
    - `.venv`가 있으면 해당 site-packages 경로를 `sys.path`에 추가합니다.
    - `.env` 파일이 있으면 환경 변수를 로드합니다.

    이 유틸은 예제 스크립트를 레포지토리 루트에서 실행하지 않아도
    동작하도록 도와줍니다.
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
