"""Responses 웹소켓 스트리밍 예제 (함수 도구, 에이전트-도구, 승인 흐름 포함).

사용자용 웹소켓 워크플로우를 `responses_websocket_session(...)`로 시연합니다:
- 스트리밍 출력(가능한 경우 reasoning summary 델타 포함)
- 일반 함수 도구(function tools)
- 전문가 에이전트를 `Agent.as_tool(...)`로 도구화
- 민감한 도구 호출에 대한 사람(HITL) 승인 흐름
- 동일 트레이스에서 `previous_response_id`를 사용하는 후속 턴

필수 환경 변수:
- `OPENAI_API_KEY`

선택 환경 변수:
- `OPENAI_MODEL` (기본값: `gpt-5.5`)
- `OPENAI_BASE_URL`
- `OPENAI_WEBSOCKET_BASE_URL`
- `EXAMPLES_INTERACTIVE_MODE=auto` (예제 자동화 모드에서 HITL 프롬프트 자동 승인)

실행 방법 (터미널 예시):
1. 가상환경 활성화(선택):
    source .venv/bin/activate
2. 필요 시 의존성 설치/동기화:
    make sync
3. 스크립트 실행:
    python examples/basic/stream_ws.py
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
import os
from typing import Any

from openai.types.shared import Reasoning

from agents import (
    Agent,
    ModelSettings,
    ResponsesWebSocketSession,
    function_tool,
    responses_websocket_session,
    trace,
)
from examples.auto_mode import confirm_with_fallback


@function_tool
def lookup_order(order_id: str) -> dict[str, Any]:
    """데모용으로 결정론적(order_id에 따라 고정된) 주문 정보를 반환합니다."""
    orders = {
        "ORD-1001": {
            "order_id": "ORD-1001",
            "status": "delivered",
            "delivered_days_ago": 3,
            "amount": 49.99,
            "currency": "USD",
            "item": "Wireless Mouse",
        },
        "ORD-2002": {
            "order_id": "ORD-2002",
            "status": "delivered",
            "delivered_days_ago": 12,
            "amount": 129.0,
            "currency": "USD",
            "item": "Keyboard",
        },
    }
    return orders.get(
        order_id,
        {
            "order_id": order_id,
            "status": "unknown",
            "delivered_days_ago": 999,
            "amount": 0.0,
            "currency": "USD",
            "item": "unknown",
        },
    )


@function_tool(needs_approval=True)
def submit_refund(order_id: str, amount: float, reason: str) -> dict[str, Any]:
    """환불 요청을 생성하는 도구입니다. 이 도구는 승인이 필요합니다."""
    ticket = "RF-1001" if order_id == "ORD-1001" else f"RF-{order_id[-4:]}"
    return {
        "refund_ticket": ticket,
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "status": "approved_pending_processing",
    }


def ask_approval(question: str) -> bool:
    """승인 허가를 요청합니다. 예제의 자동 모드에서는 자동 승인됩니다."""
    return confirm_with_fallback(f"[approval] {question} [y/N]: ", default=True)


async def run_streamed_turn(
    ws: ResponsesWebSocketSession,
    agent: Agent[Any],
    prompt: str,
    *,
    previous_response_id: str | None = None,
) -> tuple[str, str]:
    """스트리밍 방식으로 한 턴을 실행하고 필요 시 사람 승인(HITL)을 처리합니다.

    반환값은 `(response_id, final_output)` 튜플입니다.
    """
    print(f"\nUser: {prompt}\n")

    result = ws.run_streamed(
        agent,
        prompt,
        previous_response_id=previous_response_id,
    )
    printed_reasoning = False
    printed_output = False

    while True:
        async for event in result.stream_events():
            # 원시 응답 이벤트 처리(추론 요약 델타, 출력 텍스트 델타 등)
            if event.type == "raw_response_event":
                raw = event.data
                if raw.type == "response.reasoning_summary_text.delta":
                    if not printed_reasoning:
                        print("Reasoning:")
                        printed_reasoning = True
                    print(raw.delta, end="", flush=True)
                elif raw.type == "response.output_text.delta":
                    if printed_reasoning and not printed_output:
                        print("\n")
                    if not printed_output:
                        print("Assistant:")
                        printed_output = True
                    print(raw.delta, end="", flush=True)
                continue

            # run_item_stream_event: 도구 호출/결과 항목 처리
            if event.type != "run_item_stream_event":
                continue

            item = event.item
            if item.type == "tool_call_item":
                tool_name = getattr(item.raw_item, "name", "unknown")
                tool_args = getattr(item.raw_item, "arguments", "")
                print(f"\n[tool call] {tool_name}({tool_args})")
            elif item.type == "tool_call_output_item":
                print(f"[tool result] {item.output}")

        # reasoning/assistant 출력이 있었다면 줄바꿈을 추가합니다.
        if printed_reasoning or printed_output:
            print("\n")

        # 중단(interruptions)이 없다면 턴이 완료된 것입니다.
        if not result.interruptions:
            break

        # 중단이 있으면 상태로 변환하고 각 중단에 대해 승인/거부를 처리합니다.
        state = result.to_state()
        for interruption in result.interruptions:
            question = f"Approve {interruption.name} with args {interruption.arguments}?"
            if ask_approval(question):
                state.approve(interruption)
            else:
                state.reject(interruption)

        # 승인/거부 처리 후 같은 상태로 다시 실행합니다.
        result = ws.run_streamed(agent, state)

    if result.last_response_id is None:
        raise RuntimeError("The streamed run completed without a response_id.")

    final_output = str(result.final_output)
    print(f"response_id: {result.last_response_id}")
    print(f"final_output: {final_output}\n")
    return result.last_response_id, final_output


async def main() -> None:
    model_name = os.getenv("OPENAI_MODEL", "gpt-5.5")
    policy_agent = Agent(
        name="RefundPolicySpecialist",
        instructions=(
            "You are a refund policy specialist. The policy is simple: orders delivered "
            "within 7 days are eligible for a full refund, and older delivered orders "
            "are not. Return a short answer with eligibility and a one-line reason."
        ),
        model=model_name,
        model_settings=ModelSettings(max_tokens=120),
    )

    support_agent = Agent(
        name="SupportAgent",
        instructions=(
            "You are a support agent. For refund requests, do this in order: "
            "1) call lookup_order, 2) call refund_policy_specialist, 3) if the user "
            "asked to proceed and the order is eligible, call submit_refund. "
            "When asked for only the refund ticket, return only the ticket token "
            "(for example RF-1001)."
        ),
        tools=[
            lookup_order,
            policy_agent.as_tool(
                tool_name="refund_policy_specialist",
                tool_description="Check refund eligibility and explain the policy decision.",
            ),
            submit_refund,
        ],
        model=model_name,
        model_settings=ModelSettings(
            max_tokens=200,
            reasoning=Reasoning(effort="medium", summary="detailed"),
        ),
    )

    try:
        # 이 헬퍼를 건너뛰고 Runner.run_streamed(...)를 직접 호출할 수도 있습니다.
        # 하지만 그렇게 하면 각 실행에서 새 연결이 생성/연결될 수 있습니다.
        # 이 헬퍼는 턴 간(및 중첩된 agent-as-tool 실행 간)에 동일한 연결/RunConfig를
        # 재사용하기 쉽게 만들어 웹소켓 연결을 따뜻하게 유지합니다.
        async with responses_websocket_session() as ws:
            with trace("Responses WS support example") as current_trace:
                print(f"Using model={model_name}")
                print(f"trace_id={current_trace.trace_id}")

                first_response_id, _ = await run_streamed_turn(
                    ws,
                    support_agent,
                    (
                        "Customer wants a refund for order ORD-1001 because the mouse arrived "
                        "damaged. Please check the order, ask the refund policy specialist, and "
                        "if it is eligible submit the refund. Reply with only the refund ticket."
                    ),
                )

                await run_streamed_turn(
                    ws,
                    support_agent,
                    "What refund ticket did you just create? Reply with only the ticket.",
                    previous_response_id=first_response_id,
                )
    except RuntimeError as exc:
        # 웹소켓 모드가 이벤트를 보내기 전에 닫히면(계정/모델에 기능 미지원) 친절한 메시지를 출력합니다.
        if "closed before any response events" in str(exc):
            print(
                "\nWebsocket mode closed before sending events. This usually means the "
                "feature is not enabled for this account/model yet."
            )
            return
        raise


if __name__ == "__main__":
    asyncio.run(main())
