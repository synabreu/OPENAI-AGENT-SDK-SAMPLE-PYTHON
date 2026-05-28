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

from agents import Agent, AgentToolStreamEvent, ModelSettings, Runner, function_tool, trace


@function_tool(
    name_override="billing_status_checker",
    description_override="Answer questions about customer billing status.",
)
def billing_status_checker(customer_id: str | None = None, question: str = "") -> str:
    """Return a canned billing answer or a fallback when the question is unrelated."""
    normalized = question.lower()
    if "bill" in normalized or "billing" in normalized:
        return f"This customer (ID: {customer_id})'s bill is $100"
    return "I can only answer questions about billing."


def handle_stream(event: AgentToolStreamEvent) -> None:
    """Print streaming events emitted by the nested billing agent."""
    stream = event["event"]
    tool_call = event.get("tool_call")
    tool_call_info = tool_call.call_id if tool_call is not None else "unknown"
    print(f"[stream] agent={event['agent'].name} call={tool_call_info} type={stream.type} {stream}")


async def main() -> None:
    with trace("Agents as tools streaming example"):
        billing_agent = Agent(
            name="Billing Agent",
            instructions="You are a billing agent that answers billing questions.",
            model_settings=ModelSettings(tool_choice="required"),
            tools=[billing_status_checker],
        )

        billing_agent_tool = billing_agent.as_tool(
            tool_name="billing_agent",
            tool_description="You are a billing agent that answers billing questions.",
            on_stream=handle_stream,
        )

        main_agent = Agent(
            name="Customer Support Agent",
            instructions=(
                "You are a customer support agent. Always call the billing agent to answer billing "
                "questions and return the billing agent response to the user."
            ),
            tools=[billing_agent_tool],
        )

        result = await Runner.run(
            main_agent,
            "Hello, my customer ID is ABC123. How much is my bill for this month?",
        )

    print(f"\nFinal response:\n{result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
