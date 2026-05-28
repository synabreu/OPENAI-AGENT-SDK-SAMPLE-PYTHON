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
import urllib.error
import urllib.request

from openai import AsyncOpenAI

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled

set_tracing_disabled(True)

# import logging
# logging.basicConfig(level=logging.DEBUG)

# This is an example of how to use gpt-oss with Ollama.
# Refer to https://cookbook.openai.com/articles/gpt-oss/run-locally-ollama for more details.
# If you prefer using LM Studio, refer to https://cookbook.openai.com/articles/gpt-oss/run-locally-lmstudio
GPT_OSS_BASE_URL = os.getenv("GPT_OSS_BASE_URL", "http://localhost:11434/v1")
GPT_OSS_MODEL = os.getenv("GPT_OSS_MODEL", "gpt-oss:20b")


def check_gpt_oss_server() -> None:
    health_url = GPT_OSS_BASE_URL.removesuffix("/v1").removesuffix("/") + "/api/tags"
    try:
        with urllib.request.urlopen(health_url, timeout=2):
            return
    except (OSError, urllib.error.URLError) as exc:
        raise SystemExit(
            "Could not connect to a local Ollama server for the gpt-oss example.\n\n"
            f"Expected endpoint: {GPT_OSS_BASE_URL}\n"
            f"Health check failed: {exc}\n\n"
            "Start Ollama and pull the model, then run this example again:\n"
            "  ollama serve\n"
            f"  ollama pull {GPT_OSS_MODEL}\n\n"
            "If you use another OpenAI-compatible local server, set:\n"
            "  GPT_OSS_BASE_URL=http://host:port/v1\n"
            "  GPT_OSS_MODEL=your-model-name"
        ) from exc


gpt_oss_model = OpenAIChatCompletionsModel(
    model=GPT_OSS_MODEL,
    openai_client=AsyncOpenAI(
        base_url=GPT_OSS_BASE_URL,
        api_key="ollama",
    ),
)


async def main():
    check_gpt_oss_server()

    # Note that using a custom outputType for an agent may not work well with gpt-oss models.
    # Consider going with the default "text" outputType.
    # See also: https://github.com/openai/openai-agents-python/issues/1414
    agent = Agent(
        name="Assistant",
        instructions="You're a helpful assistant. You provide a concise answer to the user's question.",
        model=gpt_oss_model,
    )

    result = await Runner.run(agent, "Tell me about recursion in programming.")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
