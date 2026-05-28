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

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServerStreamableHttp


async def main():
    async with MCPServerStreamableHttp(
        name="DeepWiki MCP Streamable HTTP Server",
        params={
            "url": "https://mcp.deepwiki.com/mcp",
            # Allow more time for remote tool responses.
            "timeout": 15,
            "sse_read_timeout": 300,
        },
        # Retry slow/unstable remote calls a couple of times.
        max_retry_attempts=2,
        retry_backoff_seconds_base=2.0,
        client_session_timeout_seconds=15,
    ) as server:
        agent = Agent(
            name="DeepWiki Assistant",
            instructions="Use the tools to respond to user requests.",
            mcp_servers=[server],
        )

        trace_id = gen_trace_id()
        with trace(workflow_name="DeepWiki Streamable HTTP Example", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
            result = await Runner.run(
                agent,
                "For the repository openai/codex, tell me the primary programming language.",
            )
            print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
