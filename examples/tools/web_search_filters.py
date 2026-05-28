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
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlparse, urlunparse

from openai.types.responses.web_search_tool import Filters
from openai.types.shared.reasoning import Reasoning

from agents import Agent, ModelSettings, Runner, WebSearchTool, trace


def _get_field(obj: Any, key: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


# import logging
# logging.basicConfig(level=logging.DEBUG)


def _normalized_source_urls(sources: Any) -> list[str]:
    allowed_hosts = {"developers.openai.com", "platform.openai.com"}
    blocked_suffixes = (
        ".css",
        ".eot",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".js",
        ".png",
        ".svg",
        ".svgz",
        ".woff",
        ".woff2",
    )

    urls: list[str] = []
    seen: set[str] = set()
    if not isinstance(sources, list):
        return urls

    for source in sources:
        url = getattr(source, "url", None)
        if url is None and isinstance(source, Mapping):
            url = source.get("url")
        if not isinstance(url, str):
            continue

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc not in allowed_hosts:
            continue

        path = unquote(parsed.path).split("#", 1)[0].rstrip("/")
        if not path or path.endswith(blocked_suffixes):
            continue

        normalized = urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
        if normalized in seen:
            continue

        seen.add(normalized)
        urls.append(normalized)

    return urls


async def main():
    agent = Agent(
        name="WebOAI website searcher",
        model="gpt-5-nano",
        instructions=(
            "You are a helpful agent that searches OpenAI developer documentation and platform "
            "docs. Ignore ChatGPT help-center or end-user release notes."
        ),
        tools=[
            WebSearchTool(
                # https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses#domain-filtering
                filters=Filters(
                    allowed_domains=[
                        "developers.openai.com",
                        "platform.openai.com",
                    ],
                ),
                search_context_size="medium",
            )
        ],
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="low"),
            verbosity="low",
            # https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses#sources
            response_include=["web_search_call.action.sources"],
        ),
    )

    with trace("Web search example"):
        today = datetime.now().strftime("%Y-%m-%d")
        query = (
            "Write a summary of the latest OpenAI API and developer platform updates from the "
            f"last few weeks (today is {today}). Focus on developer docs, API changes, model "
            "release notes, and platform changelog items."
        )
        result = await Runner.run(agent, query)

        print()
        print("### Sources ###")
        print()
        for item in result.new_items:
            if item.type != "tool_call_item":
                continue

            raw_call = item.raw_item
            call_type = _get_field(raw_call, "type")
            if call_type != "web_search_call":
                continue

            action = _get_field(raw_call, "action")
            sources = _get_field(action, "sources") if action else None
            if not sources:
                continue

            for url in _normalized_source_urls(sources):
                print(f"- {url}")
        print()
        print("### Final output ###")
        print()
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
