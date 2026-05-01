# Onboarding Guide

This guide walks through dev environment setup, the codebase structure, and common extension points.

## Development environment setup

### Prerequisites

- Python 3.10 or higher
- `pip` and `virtualenv` or venv
- A terminal (bash, zsh, or compatible shell)
- NVIDIA API key from https://build.nvidia.com

### First-time setup

```bash
# Clone the repository
git clone <repo_url> && cd d-poc-mem-ra

# Create and activate virtual environment
python3.10 -m venv venv
source venv/bin/activate
# On Windows: venv\Scripts\activate

# Install in editable mode (includes dev dependencies)
pip install -e .

# Copy example environment file
cp .env.example .env

# Edit .env and add your NVIDIA_API_KEY
# (generate one at https://build.nvidia.com)
export NVIDIA_API_KEY="your_key_here"
# or add it to .env:
echo "NVIDIA_API_KEY=your_key_here" >> .env

# Verify installation
python -m src.main
# Type a research topic and press Enter to test
# Press Ctrl+C or type 'exit' to quit
```

### Quick verification

```bash
# Run the interactive agent
python -m src.main

# Example session:
# > Research the history of machine learning
# (agent decomposes topic and spawns researchers...)
```

## Project structure walkthrough

- **`src/main.py`** — Entry point. Sets up session tracking, creates the lead agent, and runs the interactive chat loop.
- **`src/core/runner.py`** — `AgentRunner` class. Implements the core agentic loop: send messages to NVIDIA NIM, handle tool calls, manage message history.
- **`src/core/schemas.py`** — OpenAI-compatible tool definitions (JSON schemas) and the `TOOL_SETS` dict that maps agent type → list of available tools.
- **`src/core/tools.py`** — Implementations of all tools: `web_search`, `write_file`, `read_file`, `glob_files`, `bash_execute`.
- **`src/core/subagent_factory.py`** — `make_agent_factory()` and `load_prompt()`. Builds agent runners with loaded prompts for researcher, data-analyst, report-writer.
- **`src/utils/transcript.py`** — `TranscriptWriter` (dual-writes to console and file) and `setup_session()` (creates timestamped session directory).
- **`src/utils/tracker.py`** — `SubagentTracker` (human-readable subagent IDs, JSONL logging of tool calls).
- **`prompts/`** — System prompts for each agent type (lead, researcher, data-analyst, report-writer). One `.txt` file per agent.

## How to add a new tool

Tools are shared across agents and defined in three places. Here is an example: adding a `get_weather(city)` tool.

### 1. Implement the tool in `src/core/tools.py`

```python
def get_weather(city: str) -> str:
    """Fetch weather for a city (example using hypothetical API)."""
    try:
        # Your implementation here
        return f"Weather in {city}: Sunny, 72°F"
    except Exception as exc:
        return f"Weather error: {exc}"
```

### 2. Add the schema in `src/core/schemas.py`

```python
GET_WEATHER = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
            },
            "required": ["city"],
        },
    },
}
```

### 3. Add to tool dispatch in `src/core/runner.py`

In the `_dispatch` method, add a case:

```python
async def _dispatch(self, name: str, args: dict) -> str:
    # ... existing cases ...
    if name == "get_weather":
        return await asyncio.to_thread(get_weather, args["city"])
    # ... rest of method
```

### 4. Update `TOOL_SETS` in `src/core/schemas.py`

Add `GET_WEATHER` to the agent types that should have access:

```python
TOOL_SETS: dict[str, list] = {
    "lead": [SPAWN_SUBAGENT],
    "researcher": [WEB_SEARCH, WRITE_FILE, GET_WEATHER],  # Added here
    "data-analyst": [GLOB_FILES, READ_FILE, BASH_EXECUTE, WRITE_FILE],
    "report-writer": [GLOB_FILES, READ_FILE, BASH_EXECUTE, WRITE_FILE],
}
```

### 5. Import the tool in `src/core/runner.py`

At the top of `runner.py`, add:

```python
from .tools import bash_execute, glob_files, read_file, web_search, write_file, get_weather
```

## How to add a new agent type

Suppose you want to add a **fact-checker** agent that validates claims. Here's the process:

### 1. Create a system prompt in `prompts/fact_checker.txt`

```
You are a fact-checker agent specialized in validating research claims.

When given claims to check:
1. Use web_search to find reliable sources
2. Compare claims against authoritative information
3. Report findings as JSON to files/fact_checks/
```

### 2. Add the agent to the factory in `src/core/subagent_factory.py`

In the `make_agent_factory` function, add to the `prompts` dict:

```python
prompts = {
    "researcher": load_prompt("researcher.txt"),
    "data-analyst": load_prompt("data_analyst.txt"),
    "report-writer": load_prompt("report_writer.txt"),
    "fact-checker": load_prompt("fact_checker.txt"),  # Added
}
```

### 3. Define tools for the new agent in `src/core/schemas.py`

Add to `TOOL_SETS`:

```python
TOOL_SETS: dict[str, list] = {
    "lead": [SPAWN_SUBAGENT],
    "researcher": [WEB_SEARCH, WRITE_FILE],
    "data-analyst": [GLOB_FILES, READ_FILE, BASH_EXECUTE, WRITE_FILE],
    "report-writer": [GLOB_FILES, READ_FILE, BASH_EXECUTE, WRITE_FILE],
    "fact-checker": [WEB_SEARCH, WRITE_FILE],  # Added
}
```

### 4. Update the lead agent prompt if needed

Edit `prompts/lead_agent.txt` to mention the new agent type:

```
Available types: researcher, data-analyst, report-writer, fact-checker
```

The lead agent can now spawn fact-checker subagents via `spawn_subagent`.

## How to swap the NVIDIA LLM model

The default model is defined in `src/core/runner.py`:

```python
DEFAULT_MODEL = "meta/llama-3.1-70b-instruct"
```

### Option A: Change the constant

Edit `src/core/runner.py` and replace with any NVIDIA NIM model, e.g.:

```python
DEFAULT_MODEL = "meta/llama-3.1-405b-instruct"
```

### Option B: Override at runtime

The model is passed to `AgentRunner` and `make_agent_factory`. You can override when creating agents in `src/main.py`:

```python
factory = make_agent_factory(
    on_spawn=on_spawn, 
    on_tool_call=on_tool_call,
    model="mistral/mistral-large"  # Use a different model
)
```

Available models can be found at https://docs.nvidia.com/nim/large-language-models/latest/getting-started.html.

## Logging and debugging

### Session structure

Each run creates a directory `logs/session_YYYYMMDD_HHMMSS/` containing:

- **`transcript.txt`** — Human-readable log of all agent responses and tool calls (for audit and debugging)
- **`tool_calls.jsonl`** — Structured JSONL, one object per line:
  ```json
  {"event": "spawn", "subagent_id": "RESEARCHER-1", "subagent_type": "researcher", "description": "...", "ts": "2025-05-01T14:30:22..."}
  {"event": "tool_call", "agent": "RESEARCHER-1", "tool": "web_search", "args_summary": "query='...'" , "ts": "2025-05-01T14:30:23..."}
  ```
- **`files/`** — Research output (notes, charts, data, reports)

### Interpreting tool_calls.jsonl

Each JSONL line is timestamped and indicates:
- **spawn** events — when a subagent was created
- **tool_call** events — when an agent invoked a tool
- **agent** — which agent (e.g., RESEARCHER-1, DATA_ANALYST-1) made the call
- **args_summary** — a truncated summary of arguments (to avoid huge files)

Example to count tool calls by agent:

```bash
jq -r '.agent' logs/session_YYYYMMDD_HHMMSS/tool_calls.jsonl | sort | uniq -c
```

### Debugging agent behaviour

1. Check `transcript.txt` for full conversation flow
2. Check `tool_calls.jsonl` for structured tool-call timeline
3. Review `files/research_notes/*.md` to see what researchers found
4. For LLM errors, set Python logging level (in `src/utils/transcript.py` or elsewhere):
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## Testing and validation

Currently there are no automated tests. To validate changes:

1. **Run a sample research query** and verify output appears in `logs/session_*/files/`
2. **Spot-check the transcript** for agent responses making sense
3. **Inspect tool_calls.jsonl** to ensure expected tools were called
4. **Manual review** of generated reports and charts

Future: test suite in `tests/` mirroring `src/` structure.
