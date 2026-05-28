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

from openai import OpenAI

from agents import Agent, FileSearchTool, Runner, trace


async def main():
    vector_store_id: str | None = None

    if vector_store_id is None:
        print("### Preparing vector store:\n")
        # Create a new vector store and index a file
        client = OpenAI()
        text = "Arrakis, the desert planet in Frank Herbert's 'Dune,' was inspired by the scarcity of water as a metaphor for oil and other finite resources."
        file_upload = client.files.create(
            file=("example.txt", text.encode("utf-8")),
            purpose="assistants",
        )
        print(f"File uploaded: {file_upload.to_dict()}")

        vector_store = client.vector_stores.create(name="example-vector-store")
        print(f"Vector store created: {vector_store.to_dict()}")

        indexed = client.vector_stores.files.create_and_poll(
            vector_store_id=vector_store.id,
            file_id=file_upload.id,
        )
        print(f"Stored files in vector store: {indexed.to_dict()}")
        vector_store_id = vector_store.id

    # Create an agent that can search the vector store
    agent = Agent(
        name="File searcher",
        instructions="You are a helpful agent. You answer only based on the information in the vector store.",
        tools=[
            FileSearchTool(
                max_num_results=3,
                vector_store_ids=[vector_store_id],
                include_search_results=True,
            )
        ],
    )

    with trace("File search example"):
        result = await Runner.run(
            agent, "Be concise, and tell me 1 sentence about Arrakis I might not know."
        )

        print("\n### Final output:\n")
        print(result.final_output)
        """
        Arrakis, the desert planet in Frank Herbert's "Dune," was inspired by the scarcity of water
        as a metaphor for oil and other finite resources.
        """

        print("\n### Output items:\n")
        print("\n".join([str(out.raw_item) + "\n" for out in result.new_items]))
        """
        {"id":"...", "queries":["Arrakis"], "results":[...]}
        """


if __name__ == "__main__":
    asyncio.run(main())
