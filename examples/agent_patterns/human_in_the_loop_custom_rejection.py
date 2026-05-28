"""Human-in-the-loop example with a custom rejection message.

This example is intentionally minimal:
1. A single sensitive tool requires human approval.
2. The first turn always issues that tool call.
3. ``tool_error_formatter`` defines the universal fallback message shape.
4. A per-call ``rejection_message`` passed to ``state.reject(...)`` overrides that fallback.
5. The example prints both the tool output and the assistant's final reply.
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

from agents import (
    Agent,
    ModelSettings,
    RunConfig,
    Runner,
    ToolErrorFormatterArgs,
    function_tool,
)
from examples.auto_mode import confirm_with_fallback


async def tool_error_formatter(args: ToolErrorFormatterArgs[None]) -> str | None:
    """Build the universal fallback output message for rejected tool calls."""
    if args.kind != "approval_rejected":
        return None
    # The default message is "Tool execution was not approved."
    return "Publish action was canceled because approval was rejected."


@function_tool(needs_approval=True)
async def publish_announcement(title: str, body: str) -> str:
    """Simulate publishing an announcement to users."""
    return f"Published announcement '{title}' with body: {body}"


def _find_formatter_output(result: object) -> str | None:
    items = getattr(result, "new_items", None)
    if not isinstance(items, list):
        return None

    for item in items:
        if getattr(item, "type", None) != "tool_call_output_item":
            continue
        output = getattr(item, "output", None)
        if isinstance(output, str):
            return output
    return None


async def main() -> None:
    agent = Agent(
        name="Operations Assistant",
        instructions=(
            "When a user asks to publish an announcement, call the publish_announcement tool directly. "
            "Do not ask the user for approval in plain text; runtime approvals handle that. "
            "If the tool call is rejected, respond with the exact rejection message and nothing else."
        ),
        model_settings=ModelSettings(tool_choice="publish_announcement"),
        tools=[publish_announcement],
    )
    run_config = RunConfig(tool_error_formatter=tool_error_formatter)
    # ``tool_error_formatter`` is the universal fallback for approval rejects.
    # A specific ``rejection_message`` passed to ``state.reject(...)`` below overrides it.

    result = await Runner.run(
        agent,
        "Please publish an announcement titled 'Office maintenance' with body "
        "'The office will close at 6 PM today.'",
        run_config=run_config,
    )

    while result.interruptions:
        print("\nApproval required:")
        state = result.to_state()
        for interruption in result.interruptions:
            print(f"- Tool: {interruption.name}")
            print(f"  Arguments: {interruption.arguments}")
            approved = confirm_with_fallback(
                "Approve this tool call? [y/N]: ",
                default=False,
            )
            if approved:
                state.approve(interruption)
            else:
                # This per-call rejection message takes precedence over ``tool_error_formatter``.
                state.reject(
                    interruption,
                    rejection_message=(
                        "Publish action was canceled because the reviewer denied approval."
                    ),
                )

        result = await Runner.run(agent, state, run_config=run_config)

    formatter_output = _find_formatter_output(result)
    if formatter_output:
        print("\nFormatter output:")
        print(formatter_output)

    print("\nFinal output:")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
