# NVIDIA NIM Research Agent

## Project overview

This is a multi-agent research system that orchestrates parallel AI agents to investigate topics, extract insights, and generate PDF reports with charts. It uses NVIDIA NIM LLMs (OpenAI-compatible API) and is a rewrite of the Anthropic claude-agent-sdk-demos research-agent without dependency on the Claude Agent SDK.

## Vision

Enable rapid, AI-driven research workflows where a lead agent decomposes complex topics into parallel research tasks, coordinates specialized agents for data gathering and analysis, and synthesizes findings into polished reports with visualizations.

## What this project is not

- Not a general-purpose chatbot — it is purpose-built for multi-step research workflows
- Not a web scraper — it uses web search to find public information, not deep crawling
- Not a data pipeline tool — it generates research output on demand, not for continuous ETL
- Not a replacement for human domain expertise — agents assist research, they do not replace it

## Bootstrap demo

```bash
# Clone the repo
git clone <repo_url> && cd d-poc-mem-ra

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env and add your NVIDIA_API_KEY (get it at https://build.nvidia.com)

# Run the agent
python -m src.main

# Enter a research topic when prompted:
# > Research the history of artificial intelligence
# (Control+C or type 'exit' to quit)

# Session outputs appear in logs/ with subdirectories:
# logs/session_YYYYMMDD_HHMMSS/
#   ├── transcript.txt              # Full conversation log
#   ├── tool_calls.jsonl            # Structured tool-call log
#   └── files/
#       ├── research_notes/         # Markdown notes from researcher agents
#       ├── charts/                 # PNG charts from data-analyst
#       ├── data/                   # Data summary JSON/Markdown
#       └── reports/                # Final PDF report
```

## Project structure

```
.
├── src/                        # Application source code
│   ├── main.py                 # Entry point; interactive chat loop
│   ├── core/
│   │   ├── runner.py           # AgentRunner: agentic tool-call loop
│   │   ├── schemas.py          # OpenAI tool schemas per agent type
│   │   ├── tools.py            # Tool implementations
│   │   └── subagent_factory.py # Factory producing AgentRunner per agent type
│   └── utils/
│       ├── transcript.py       # TranscriptWriter; session setup
│       └── tracker.py          # SubagentTracker; structured JSONL logging
├── prompts/                    # System prompts for each agent
│   ├── lead_agent.txt
│   ├── researcher.txt
│   ├── data_analyst.txt
│   └── report_writer.txt
├── docs/                       # Documentation
│   ├── guides/                 # How-to guides
│   ├── references/             # API and config references
│   └── knowledge-base/         # Operational knowledge and FAQs
├── pyproject.toml              # Project metadata and dependencies
├── .env.example                # Environment variable template
└── .gitignore                  # Git ignore rules
```

## Architecture

### Agent hierarchy

**Lead Agent** orchestrates the research workflow:
1. Receives a research topic from the user
2. Decomposes it into 2–4 subtopics
3. Spawns **researcher subagents** in parallel (all spawn calls issued in one LLM turn, executed concurrently via `asyncio.gather`)
4. Waits for all researchers to complete
5. Spawns a **data-analyst subagent** to extract quantitative insights and generate charts
6. Spawns a **report-writer subagent** to synthesize findings into a PDF with embedded visuals

### Tool-call loop

Each agent runs the same core loop in `AgentRunner`:
1. Send `messages` to NVIDIA NIM API (OpenAI-compatible)
2. Receive response with optional `tool_calls`
3. If no tool calls, return final text response
4. Otherwise, execute all tool calls concurrently (spawning subagents runs in parallel)
5. Append results to message history and repeat

### Agent capabilities by type

| Agent | Tools | Typical workflow |
|-------|-------|------------------|
| **lead** | `spawn_subagent` | Decompose topic → spawn researchers, data-analyst, report-writer |
| **researcher** | `web_search`, `write_file` | Search internet → save markdown notes to `files/research_notes/` |
| **data-analyst** | `glob_files`, `read_file`, `bash_execute`, `write_file` | Read notes → extract data → generate matplotlib charts → save to `files/charts/` |
| **report-writer** | `glob_files`, `read_file`, `bash_execute`, `write_file` | Read notes + charts + data → generate PDF report with reportlab |

## Configuration

| Variable | Source | Default | Description |
|----------|--------|---------|-------------|
| `NVIDIA_API_KEY` | `.env` or shell | None (required) | API key from https://build.nvidia.com |
| `DEFAULT_MODEL` | `src/core/runner.py` | `meta/llama-3.1-70b-instruct` | LLM model to use; any NVIDIA NIM model accepted |
| `NVIDIA_BASE_URL` | `src/core/runner.py` | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible API endpoint |

## Output structure

Each session creates a timestamped directory under `logs/session_YYYYMMDD_HHMMSS/`:

```
logs/session_20250501_143022/
├── transcript.txt              # Full console output (for audit/debugging)
├── tool_calls.jsonl            # Structured JSONL log of all tool calls
└── files/                       # Research artifacts
    ├── research_notes/
    │   └── *.md                # Researcher output: markdown notes
    ├── charts/
    │   └── *.png               # Data-analyst output: matplotlib charts
    ├── data/
    │   └── data_summary.md     # Data-analyst output: quantitative summary
    └── reports/
        └── *.pdf               # Report-writer output: final PDF report
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| openai | ≥1.0.0 | OpenAI-compatible client for NVIDIA NIM API |
| duckduckgo-search | ≥6.0.0 | Web search (no API key required) |
| python-dotenv | ≥1.0.0 | Load `.env` configuration |
| reportlab | ≥4.0.0 | PDF generation |
| matplotlib | ≥3.8.0 | Chart generation |
| Python | ≥3.10 | Async/await syntax and type hints |

## Further reading

- **Getting started**: see [`docs/guides/onboarding.md`](docs/guides/onboarding.md) for dev setup and contributing
- **Configuration**: see [`docs/references/config.md`](docs/references/config.md) for all environment variables and constants
- **API reference**: see [`docs/references/api.md`](docs/references/api.md) for Python class and function signatures
- **Lessons learned**: see [`docs/knowledge-base/lessons-learned.md`](docs/knowledge-base/lessons-learned.md) for architectural decisions and troubleshooting
