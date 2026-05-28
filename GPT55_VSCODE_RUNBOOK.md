# GPT-5.5 Agents SDK samples in VSCode

This workspace includes a runnable GPT-5.5 sample suite at:

```bash
examples/gpt55_feature_samples.py
```

It covers these features without using `FakeModel`:

- `hello`
- `tools`
- `structured`
- `handoff`
- `agents-as-tools`
- `guardrails`
- `streaming`
- `memory`
- `tracing`
- `all`

## Setup on macOS

```bash
cd /Users/synabreu/Documents/Codex/2026-05-25/openai-agent-sdk-sample-python
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install python-dotenv
cp .env.example .env
```

Edit `.env` and set your real API key:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.5
OPENAI_REASONING_EFFORT=low
OPENAI_VERBOSITY=low
```

## Run from terminal

```bash
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature hello
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature tools
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature structured
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature handoff
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature agents-as-tools
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature guardrails
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature streaming
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature memory
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature tracing
PYTHONPATH=src .venv/bin/python -m examples.gpt55_feature_samples --feature all
```

## Run from VSCode

1. Open this folder in VSCode.
2. Select the Python interpreter at `.venv/bin/python`.
3. Open the Run and Debug panel.
4. Choose one of the `GPT-5.5 sample: ...` launch configurations.
5. Press Run.

The VSCode settings already point to `.venv/bin/python`, load `${workspaceFolder}/.env`, and set `PYTHONPATH` to `${workspaceFolder}/src`.
