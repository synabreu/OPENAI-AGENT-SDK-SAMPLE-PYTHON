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
import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from openai.types.responses import ResponseFunctionShellToolCall
from openai.types.responses.response_container_reference import ResponseContainerReference

from agents import Agent, Runner, ShellTool, ShellToolInlineSkill, trace
from agents.items import ModelResponse

SKILL_NAME = "csv-workbench"
SKILL_DIR = Path(__file__).resolve().parent / "skills" / SKILL_NAME


def build_skill_zip_bundle() -> bytes:
    with TemporaryDirectory(prefix="agents-inline-skill-") as temp_dir:
        zip_path = Path(temp_dir) / f"{SKILL_NAME}.zip"
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(SKILL_DIR.rglob("*")):
                if path.is_file():
                    archive.write(path, f"{SKILL_NAME}/{path.relative_to(SKILL_DIR)}")
        return zip_path.read_bytes()


def build_inline_skill() -> ShellToolInlineSkill:
    bundle = build_skill_zip_bundle()
    return {
        "type": "inline",
        "name": SKILL_NAME,
        "description": "Analyze CSV files in /mnt/data and return concise numeric summaries.",
        "source": {
            "type": "base64",
            "media_type": "application/zip",
            "data": base64.b64encode(bundle).decode("ascii"),
        },
    }


def extract_container_id(raw_responses: list[ModelResponse]) -> str | None:
    for response in raw_responses:
        for item in response.output:
            if isinstance(item, ResponseFunctionShellToolCall) and isinstance(
                item.environment, ResponseContainerReference
            ):
                return item.environment.container_id

    return None


async def main(model: str) -> None:
    inline_skill = build_inline_skill()

    with trace("container_shell_inline_skill_example"):
        agent1 = Agent(
            name="Container Shell Agent (Inline Skill)",
            model=model,
            instructions="Use the available container skill to answer user requests.",
            tools=[
                ShellTool(
                    environment={
                        "type": "container_auto",
                        "network_policy": {"type": "disabled"},
                        "skills": [inline_skill],
                    }
                )
            ],
        )

        result1 = await Runner.run(
            agent1,
            (
                "Use the csv-workbench skill. Create /mnt/data/orders.csv with columns "
                "id,region,amount,status and at least 6 rows. Then report total amount by "
                "region and count failed orders."
            ),
        )
        print(f"Agent: {result1.final_output}")

        container_id = extract_container_id(result1.raw_responses)
        if not container_id:
            raise RuntimeError("Container ID was not returned in shell call output.")

        print(f"[info] Reusing container_id={container_id}")

        agent2 = Agent(
            name="Container Reference Shell Agent",
            model=model,
            instructions="Reuse the existing shell container and answer concisely.",
            tools=[
                ShellTool(
                    environment={
                        "type": "container_reference",
                        "container_id": container_id,
                    }
                )
            ],
        )

        result2 = await Runner.run(
            agent2,
            "Run `ls -la /mnt/data`, then summarize in one sentence.",
        )
        print(f"Agent (container reuse): {result2.final_output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default="gpt-5.5",
        help="Model name to use.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.model))
