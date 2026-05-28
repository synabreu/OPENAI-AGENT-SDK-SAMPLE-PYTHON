"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/retry.py

이 예제는 재시도(retry) 정책과 설정을 구성하고, 정책이 재시도 여부를
어떻게 결정하는지 로그로 보여줍니다.
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
import inspect

from agents import (
    Agent,
    ModelRetrySettings,
    ModelSettings,
    RetryDecision,
    RunConfig,
    Runner,
    retry_policies,
)


def format_error(error: object) -> str:
    """
    오류 객체를 사람이 읽기 좋은 문자열로 변환합니다.

    예외가 아닌 객체가 들어오면 "Unknown error"를 반환합니다.
    """
    if not isinstance(error, BaseException):
        return "Unknown error"
    return str(error) or error.__class__.__name__


async def main() -> None:
    # 재시도 정책들을 조합합니다.
    # provider_suggested(): OpenAI 기반 모델의 헤더(x-should-retry 등)에 따른
    # 공급자 권장 재시도 규칙을 따릅니다(예: 408/409/429/5xx 등).
    apply_policies = retry_policies.any(
        retry_policies.provider_suggested(),
        retry_policies.retry_after(),
        retry_policies.network_error(),
        retry_policies.http_status([408, 409, 429, 500, 502, 503, 504]),
    )

    async def policy(context) -> bool | RetryDecision:
        """
        재시도 정책 평가 함수.

        - `context`에는 현재 시도 정보, 오류, 시도 횟수 제한 등이 포함됩니다.
        - 반환값은 `bool` 또는 `RetryDecision`으로, 재시도 여부와 지연 시간을 포함할 수 있습니다.
        """
        raw_decision = apply_policies(context)
        decision: bool | RetryDecision
        if inspect.isawaitable(raw_decision):
            decision = await raw_decision
        else:
            decision = raw_decision
        if isinstance(decision, RetryDecision):
            # RetryDecision 객체는 상세한 재시도 결정을 포함합니다.
            if not decision.retry:
                print(
                    f"[retry] stop after attempt {context.attempt}/{context.max_retries + 1}: "
                    f"{format_error(context.error)}"
                )
                return False

            # 재시도 로그: 시도번호, 대기시간(또는 기본 백오프), 이유, 오류
            print(
                " | ".join(
                    part
                    for part in [
                        f"[retry] retry attempt {context.attempt}/{context.max_retries + 1}",
                        (
                            f"waiting {decision.delay:.2f}s"
                            if decision.delay is not None
                            else "using default backoff"
                        ),
                        f"reason: {decision.reason}" if decision.reason else None,
                        f"error: {format_error(context.error)}",
                    ]
                    if part is not None
                )
            )
            return decision

        if not decision:
            print(
                f"[retry] stop after attempt {context.attempt}/{context.max_retries + 1}: "
                f"{format_error(context.error)}"
            )
        return decision

    retry = ModelRetrySettings(
        max_retries=4,
        backoff={
            "initial_delay": 0.5,
            "max_delay": 5.0,
            "multiplier": 2.0,
            "jitter": True,
        },
        policy=policy,
    )

    # RunConfig 수준의 model_settings는 실행 전체에 대한 공통 기본값입니다.
    # 개별 Agent가 model_settings를 정의하면 겹치는 키는 Agent 쪽이 우선하지만,
    # retry/backoff와 같은 중첩 객체는 병합됩니다.
    run_config = RunConfig(model_settings=ModelSettings(retry=retry))

    agent = Agent(
        name="Assistant",
        instructions="You are a concise assistant. Answer in 3 short bullet points at most.",
        # This Agent repeats the same retry config for clarity. In real code you
        # 이 Agent는 명확성을 위해 동일한 재시도 설정을 다시 지정합니다. 실제 코드에서는
        # 공통 기본값을 RunConfig에 두고, 에이전트별로 다른 동작이 필요할 때만 오버라이드하세요.
        model_settings=ModelSettings(retry=retry),
    )

    print(
        "Retry support is configured. You will only see [retry] logs if a transient failure happens."
    )

    result = await Runner.run(
        agent,
        "Explain exponential backoff for API retries in plain English.",
        run_config=run_config,
    )

    print("\nFinal output:\n")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
