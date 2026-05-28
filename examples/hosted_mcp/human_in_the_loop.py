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

import argparse
import asyncio
import json
from typing import Literal

from agents import Agent, HostedMCPTool, ModelSettings, Runner, RunResult, RunResultStreaming
from examples.auto_mode import confirm_with_fallback


def prompt_for_interruption(
    tool_name: str | None, arguments: str | dict[str, object] | None
) -> bool:
    params: object = {}
    if arguments:
        if isinstance(arguments, str):
            try:
                params = json.loads(arguments)
            except json.JSONDecodeError:
                params = arguments
        else:
            params = arguments
    try:
        return confirm_with_fallback(
            f"Approve running tool (mcp: {tool_name or 'unknown'}, params: {json.dumps(params)})? (y/n) ",
            default=True,
        )
    except (EOFError, KeyboardInterrupt):
        return False


async def _drain_stream(
    result: RunResultStreaming,
    verbose: bool,
) -> RunResultStreaming:
    async for event in result.stream_events():
        if verbose:
            print(event)
        elif event.type == "raw_response_event" and event.data.type == "response.output_text.delta":
            print(event.data.delta, end="", flush=True)
    if not verbose:
        print()
    return result


async def main(verbose: bool, stream: bool) -> None:
    require_approval: Literal["always"] = "always"
    agent = Agent(
        name="MCP Assistant",
        instructions=(
            "You must always use the MCP tools to answer questions. "
            "Use the DeepWiki hosted MCP server to answer questions and do not ask the user for "
            "additional configuration."
        ),
        model_settings=ModelSettings(tool_choice="required"),
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "deepwiki",
                    "server_url": "https://mcp.deepwiki.com/mcp",
                    "require_approval": require_approval,
                }
            )
        ],
    )

    question = "Which language is the repository openai/codex written in?"

    run_result: RunResult | RunResultStreaming
    if stream:
        stream_result = Runner.run_streamed(agent, question, max_turns=100)
        stream_result = await _drain_stream(stream_result, verbose)
        while stream_result.interruptions:
            state = stream_result.to_state()
            for interruption in stream_result.interruptions:
                approved = prompt_for_interruption(interruption.name, interruption.arguments)
                if approved:
                    state.approve(interruption)
                else:
                    state.reject(interruption)
            stream_result = Runner.run_streamed(agent, state, max_turns=100)
            stream_result = await _drain_stream(stream_result, verbose)
        print(f"Done streaming; final result: {stream_result.final_output}")
        run_result = stream_result
    else:
        run_result = await Runner.run(agent, question, max_turns=100)
        while run_result.interruptions:
            state = run_result.to_state()
            for interruption in run_result.interruptions:
                approved = prompt_for_interruption(interruption.name, interruption.arguments)
                if approved:
                    state.approve(interruption)
                else:
                    state.reject(interruption)
            run_result = await Runner.run(agent, state, max_turns=100)
        print(run_result.final_output)

    if verbose:
        for item in run_result.new_items:
            print(item)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true", default=False)
    parser.add_argument("--stream", action="store_true", default=False)
    args = parser.parse_args()

    asyncio.run(main(args.verbose, args.stream))
