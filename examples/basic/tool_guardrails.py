import os as _os
import sys as _sys
from pathlib import Path as _Path

"""터미널에서 예제를 실행하는 방법(한글 설명)

1. (선택) 가상환경 활성화(포함된 `.venv` 사용 시):
    source .venv/bin/activate

2. (선택) 의존성 설치/동기화:
    make sync

3. 예제 실행:
    python examples/basic/tool_guardrails.py

이 예제는 도구 입력/출력에 대한 가드레일(guardrails)을 시연합니다.
예: 입력에 민감 단어가 포함되면 호출을 차단하거나, 출력에 민감한 데이터가
포함되면 예외를 발생시키는 방식입니다.
"""


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
import json

from agents import (
    Agent,
    Runner,
    ToolGuardrailFunctionOutput,
    ToolInputGuardrailData,
    ToolOutputGuardrailData,
    ToolOutputGuardrailTripwireTriggered,
    function_tool,
    tool_input_guardrail,
    tool_output_guardrail,
)


@function_tool
def send_email(to: str, subject: str, body: str) -> str:
    """지정된 수신자에게 이메일을 보내는 도구 함수입니다.

    실제로는 전송을 시뮬레이션하며 성공 메시지를 반환합니다.
    """
    return f"Email sent to {to} with subject '{subject}'"


@function_tool
def get_user_data(user_id: str) -> dict[str, str]:
    """사용자 ID로 사용자 데이터를 조회하는 도구 함수입니다.

    데모 목적으로 민감한 데이터(예: SSN)를 포함한 샘플 데이터를 반환합니다.
    실제 시스템에서는 민감 데이터 노출을 방지해야 합니다.
    """
    # 민감 데이터를 포함한 응답을 시뮬레이션합니다
    return {
        "user_id": user_id,
        "name": "John Doe",
        "email": "john@example.com",
        "ssn": "123-45-6789",  # 민감 정보(예: 주민등록번호/SSN) — 차단 대상
        "phone": "555-1234",
    }


@function_tool
def get_contact_info(user_id: str) -> dict[str, str]:
    """연락처 정보를 조회하는 도구 함수입니다."""
    return {
        "user_id": user_id,
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "555-1234",
    }


@tool_input_guardrail
def reject_sensitive_words(data: ToolInputGuardrailData) -> ToolGuardrailFunctionOutput:
    """도구 호출의 인수에 민감 단어가 포함되어 있으면 호출을 거부하는 입력 가드레일입니다."""
    try:
        args = json.loads(data.context.tool_arguments) if data.context.tool_arguments else {}
    except json.JSONDecodeError:
        return ToolGuardrailFunctionOutput(output_info="Invalid JSON arguments")

    # 의심스러운 내용(민감 단어) 검사
    sensitive_words = [
        "password",
        "hack",
        "exploit",
        "malware",
        "ACME",
    ]
    for key, value in args.items():
        value_str = str(value).lower()
        for word in sensitive_words:
            if word.lower() in value_str:
                # 도구 호출을 거부하고, 함수가 호출되지 않았음을 모델에 알립니다
                return ToolGuardrailFunctionOutput.reject_content(
                    message=f"🚨 Tool call blocked: contains '{word}'",
                    output_info={"blocked_word": word, "argument": key},
                )

    return ToolGuardrailFunctionOutput(output_info="Input validated")


@tool_output_guardrail
def block_sensitive_output(data: ToolOutputGuardrailData) -> ToolGuardrailFunctionOutput:
    """출력에 민감한 데이터가 포함되어 있으면 예외로 실행을 중단하는 출력 가드레일입니다."""
    output_str = str(data.output).lower()

    # 민감한 데이터 패턴 검사
    if "ssn" in output_str or "123-45-6789" in output_str:
        # 민감 데이터가 포함되면 raise_exception을 사용해 실행을 완전히 중단합니다.
        return ToolGuardrailFunctionOutput.raise_exception(
            output_info={"blocked_pattern": "SSN", "tool": data.context.tool_name},
        )

    return ToolGuardrailFunctionOutput(output_info="Output validated")


@tool_output_guardrail
def reject_phone_numbers(data: ToolOutputGuardrailData) -> ToolGuardrailFunctionOutput:
    """전화번호가 포함된 함수 출력을 거부하는 출력 가드레일입니다."""
    output_str = str(data.output)
    if "555-1234" in output_str:
        return ToolGuardrailFunctionOutput.reject_content(
            message="User data not retrieved as it contains a phone number which is restricted.",
            output_info={"redacted": "phone_number"},
        )
    return ToolGuardrailFunctionOutput(output_info="Phone number check passed")


# Apply guardrails to tools
send_email.tool_input_guardrails = [reject_sensitive_words]
get_user_data.tool_output_guardrails = [block_sensitive_output]
get_contact_info.tool_output_guardrails = [reject_phone_numbers]

# 에이전트 정의: 이메일 및 사용자 데이터 도구에 접근 가능한 보안 보조 에이전트
agent = Agent(
    name="Secure Assistant",
    instructions="You are a helpful assistant with access to email and user data tools.",
    tools=[send_email, get_user_data, get_contact_info],
)


async def main():
    print("=== Tool Guardrails Example ===\n")

    try:
        # 예제 1: 정상 동작 — 이메일 전송이 정상적으로 수행됩니다.
        print("1. Normal email sending:")
        result = await Runner.run(agent, "Send a welcome email to john@example.com")
        print(f"✅ Successful tool execution: {result.final_output}\n")

        # 예제 2: 입력 가드레일 작동 — 도구 호출이 거부되지만 실행은 계속됩니다.
        print("2. Attempting to send email with suspicious content:")
        result = await Runner.run(
            agent, "Send an email to john@example.com introducing the company ACME corp."
        )
        print(f"❌ Guardrail rejected function tool call: {result.final_output}\n")
    except Exception as e:
        print(f"Error: {e}\n")

    try:
        # 예제 3: 출력 가드레일 작동 — 민감 데이터 포함 시 예외 발생
        print("3. Attempting to get user data (contains SSN). Execution blocked:")
        result = await Runner.run(agent, "Get the data for user ID user123")
        print(f"✅ Successful tool execution: {result.final_output}\n")
    except ToolOutputGuardrailTripwireTriggered as e:
        print("🚨 Output guardrail triggered: Execution halted for sensitive data")
        print(f"Details: {e.output.output_info}\n")

    try:
        # 예제 4: 출력 가드레일 작동 — 전화번호 포함 출력은 거부되고 실행은 계속됩니다.
        print("4. Rejecting function tool output containing phone numbers:")
        result = await Runner.run(agent, "Get contact info for user456")
        print(f"❌ Guardrail rejected function tool output: {result.final_output}\n")
    except Exception as e:
        print(f"Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())

"""
Example output:

=== Tool Guardrails Example ===

1. Normal email sending:
✅ Successful tool execution: I've sent a welcome email to john@example.com with an appropriate subject and greeting message.

2. Attempting to send email with suspicious content:
❌ Guardrail rejected function tool call: I'm unable to send the email as mentioning ACME Corp. is restricted.

3. Attempting to get user data (contains SSN). Execution blocked:
🚨 Output guardrail triggered: Execution halted for sensitive data
   Details: {'blocked_pattern': 'SSN', 'tool': 'get_user_data'}

4. Rejecting function tool output containing sensitive data:
❌ Guardrail rejected function tool output: I'm unable to retrieve the contact info for user456 because it contains restricted information.
"""
