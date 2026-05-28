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
from pathlib import Path

from agents import Agent, Runner, ShellTool, ShellToolLocalSkill, trace
from examples.tools.shell import ShellExecutor

SKILL_NAME = "csv-workbench"
SKILL_DIR = Path(__file__).resolve().parent / "skills" / SKILL_NAME


def build_local_skill() -> ShellToolLocalSkill:
    return {
        "name": SKILL_NAME,
        "description": "Analyze CSV files and return concise numeric summaries.",
        "path": str(SKILL_DIR),
    }


async def main(model: str) -> None:
    local_skill = build_local_skill()

    with trace("local_shell_skill_example"):
        agent1 = Agent(
            name="Local Shell Agent (Local Skill)",
            model=model,
            instructions="Use the available local skill to answer user requests.",
            tools=[
                ShellTool(
                    environment={
                        "type": "local",
                        "skills": [local_skill],
                    },
                    executor=ShellExecutor(),
                )
            ],
        )

        result1 = await Runner.run(
            agent1,
            (
                "Use the csv-workbench skill. Create /tmp/test_orders.csv with columns "
                "id,region,amount,status and at least 6 rows. Then report total amount by "
                "region and count failed orders."
            ),
        )
        print(f"Agent: {result1.final_output}")

        agent2 = Agent(
            name="Local Shell Agent (Reuse)",
            model=model,
            instructions="Reuse the existing local shell and answer concisely.",
            tools=[
                ShellTool(
                    environment={
                        "type": "local",
                    },
                    executor=ShellExecutor(),
                )
            ],
        )

        result2 = await Runner.run(
            agent2,
            "Run `ls -la /tmp/test_orders.csv`, then summarize in one sentence.",
        )
        print(f"Agent (reuse): {result2.final_output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default="gpt-5.5",
        help="Model name to use.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.model))
