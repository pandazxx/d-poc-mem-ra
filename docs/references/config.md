# Configuration Reference

All configuration for the NVIDIA NIM Research Agent.

## Environment variables

| Variable | Source | Required | Default | Description |
|----------|--------|----------|---------|-------------|
| `NVIDIA_API_KEY` | `.env` or shell | Yes | None | API key for NVIDIA NIM API. Get one at https://build.nvidia.com |

Set in `.env`:
```
NVIDIA_API_KEY=nvapi_xxxxxxxxxxxxxxxxxxxx
```

Or export in shell:
```bash
export NVIDIA_API_KEY="nvapi_xxxxxxxxxxxxxxxxxxxx"
python -m src.main
```

## Constants

### Model and API endpoint

Defined in `src/core/runner.py`:

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_MODEL` | `meta/llama-3.1-70b-instruct` | Default NVIDIA NIM model for all agents |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible API endpoint |

To change the default model, edit `src/core/runner.py`:

```python
DEFAULT_MODEL = "meta/llama-3.1-405b-instruct"  # or any other NVIDIA NIM model
```

### LLM generation parameters

Defined in `src/core/runner.py` in `AgentRunner.run()`:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `temperature` | 0.6 | Randomness in token selection (0–1) |
| `top_p` | 0.95 | Nucleus sampling threshold |
| `max_tokens` | 4096 | Maximum response length |

These are tuned for research tasks. To adjust, edit the `client.chat.completions.create()` call in `AgentRunner.run()`.

## Paths and directories

| Path | Created by | Purpose |
|------|------------|---------|
| `logs/` | `setup_session()` | Root directory for all session logs |
| `logs/session_YYYYMMDD_HHMMSS/` | `setup_session()` | Per-session directory (timestamp at start of run) |
| `logs/session_*/transcript.txt` | `TranscriptWriter` | Human-readable console output transcript |
| `logs/session_*/tool_calls.jsonl` | `SubagentTracker` | Structured JSONL log of all tool calls and spawns |
| `logs/session_*/files/research_notes/` | `researcher` agents | Markdown notes from web searches |
| `logs/session_*/files/charts/` | `data-analyst` agent | PNG charts from matplotlib |
| `logs/session_*/files/data/` | `data-analyst` agent | Data summaries and JSON |
| `logs/session_*/files/reports/` | `report-writer` agent | Final PDF reports |

Paths are hardcoded in agent prompts. To change output location, edit the respective prompts in `prompts/`.

## Tool availability by agent type

Defined in `src/core/schemas.py` in the `TOOL_SETS` dict:

| Agent | Tools | Notes |
|-------|-------|-------|
| `lead` | `spawn_subagent` | Only tool; delegates all work to subagents |
| `researcher` | `web_search`, `write_file` | Searches web and saves markdown notes |
| `data-analyst` | `glob_files`, `read_file`, `bash_execute`, `write_file` | Processes research notes, generates charts with Python |
| `report-writer` | `glob_files`, `read_file`, `bash_execute`, `write_file` | Synthesizes notes into PDF with reportlab |

See [`docs/guides/onboarding.md`](../guides/onboarding.md) for how to add tools or agent types.

## System prompts

Stored in `prompts/` directory:

| File | Agent | Description |
|------|-------|-------------|
| `lead_agent.txt` | Lead | Orchestrates topic decomposition and subagent spawning |
| `researcher.txt` | Researcher | Conducts web searches and saves findings |
| `data_analyst.txt` | Data-analyst | Extracts data and generates matplotlib charts |
| `report_writer.txt` | Report-writer | Synthesizes findings into PDF |

Prompts are loaded at runtime by `src/core/subagent_factory.py`. To edit agent behavior, modify the corresponding `.txt` file.

## Dependencies and versions

Defined in `pyproject.toml`:

| Package | Version | Purpose |
|---------|---------|---------|
| openai | ≥1.0.0 | OpenAI-compatible client for NVIDIA NIM API |
| duckduckgo-search | ≥6.0.0 | Web search (no API key required) |
| python-dotenv | ≥1.0.0 | Load `.env` file |
| reportlab | ≥4.0.0 | PDF generation |
| matplotlib | ≥3.8.0 | Chart generation |
| Python | ≥3.10 | Language runtime |

Install with:
```bash
pip install -e .
```

## Logging levels

By default, debug logging from HTTP libraries is suppressed in `src/utils/transcript.py`:

```python
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
```

To enable debug output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Then run `python -m src.main`.
