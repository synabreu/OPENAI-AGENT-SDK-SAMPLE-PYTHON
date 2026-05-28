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
import os
from datetime import datetime

from agents import Agent, HostedMCPTool, Runner, RunResult, RunResultStreaming

# import logging
# logging.basicConfig(level=logging.DEBUG)


async def main(verbose: bool, stream: bool):
    # 1. Visit https://developers.google.com/oauthplayground/
    # 2. Input https://www.googleapis.com/auth/calendar.events as the required scope
    # 3. Grab the access token starting with "ya29."
    authorization = os.environ["GOOGLE_CALENDAR_AUTHORIZATION"]
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant that can help a user with their calendar.",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "google_calendar",
                    # see https://platform.openai.com/docs/guides/tools-connectors-mcp#connectors
                    "connector_id": "connector_googlecalendar",
                    "authorization": authorization,
                    "require_approval": "never",
                }
            )
        ],
    )

    today = datetime.now().strftime("%Y-%m-%d")
    run_result: RunResult | RunResultStreaming
    if stream:
        run_result = Runner.run_streamed(agent, f"What is my schedule for {today}?")
        async for event in run_result.stream_events():
            if event.type == "raw_response_event":
                if event.data.type.startswith("response.output_item"):
                    print(json.dumps(event.data.to_dict(), indent=2))
                if event.data.type.startswith("response.mcp"):
                    print(json.dumps(event.data.to_dict(), indent=2))
                if event.data.type == "response.output_text.delta":
                    print(event.data.delta, end="", flush=True)
        print()
    else:
        run_result = await Runner.run(agent, f"What is my schedule for {today}?")
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
