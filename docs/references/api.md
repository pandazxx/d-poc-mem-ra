# API Reference

Python API for the NVIDIA NIM Research Agent.

## Core classes

### `AgentRunner`

Main class that runs a single agent in an agentic loop.

**Location:** `src/core/runner.py`

#### `__init__()`

```python
def __init__(
    self,
    system_prompt: str,
    agent_type: str,
    model: str = DEFAULT_MODEL,
    agent_factory: Optional[Callable[["str"], "AgentRunner"]] = None,
    on_spawn: Optional[Callable[[str, str], None]] = None,
    on_tool_call: Optional[Callable[[str, str, dict], None]] = None,
)
```

**Parameters:**
- `system_prompt` (str): System prompt defining agent role and instructions
- `agent_type` (str): Type of agent ("lead", "researcher", "data-analyst", "report-writer")
- `model` (str): NVIDIA NIM model name (default: `meta/llama-3.1-70b-instruct`)
- `agent_factory` (Callable): Factory function that returns an `AgentRunner` for spawning subagents
- `on_spawn` (Callable): Callback when a subagent is spawned: `on_spawn(subagent_type: str, description: str) -> None`
- `on_tool_call` (Callable): Callback when a tool is called: `on_tool_call(agent_type: str, tool_name: str, args: dict) -> None`

**Example:**
```python
from src.core.runner import AgentRunner
from src.core.subagent_factory import load_prompt, make_agent_factory

system_prompt = load_prompt("researcher.txt")
runner = AgentRunner(
    system_prompt=system_prompt,
    agent_type="researcher",
    model="meta/llama-3.1-70b-instruct",
)
result = await runner.run("Research AI safety...")
print(result)
```

#### `run(user_prompt: str) -> str`

Run the agent on a user prompt until it produces a final text response (no more tool calls).

**Parameters:**
- `user_prompt` (str): The user's request or task

**Returns:**
- `str`: Final text response from the agent

**Behavior:**
1. Initialize message history with system prompt and user message
2. Call NVIDIA NIM API (OpenAI-compatible)
3. If response contains tool calls, execute all concurrently (via `asyncio.gather`)
4. Append tool results to message history
5. Repeat steps 2–4 until response contains no tool calls
6. Return final text response

**Example:**
```python
result = await runner.run("Research quantum computing applications")
print(result)  # Agent response with all tool executions completed
```

#### Attributes

- `messages` (list[dict]): Current message history (role + content format)
- `system_prompt` (str): The system prompt in use
- `agent_type` (str): Agent type
- `model` (str): Model name
- `tools` (list): Tools available to this agent (from `TOOL_SETS`)
- `client` (AsyncOpenAI): OpenAI client configured for NVIDIA NIM

---

### `SubagentTracker`

Lightweight tracker for subagent spawns and tool calls with structured JSONL logging.

**Location:** `src/utils/tracker.py`

#### `__init__()`

```python
def __init__(
    self,
    transcript_writer=None,
    session_dir: Optional[Path] = None,
)
```

**Parameters:**
- `transcript_writer` (TranscriptWriter): Optional transcript writer for console logging
- `session_dir` (Path): Directory to write `tool_calls.jsonl` log file

#### `register_spawn(subagent_type: str, description: str) -> str`

Register a new subagent spawn and return a unique human-readable ID.

**Parameters:**
- `subagent_type` (str): Type of agent being spawned
- `description` (str): Brief description of the task

**Returns:**
- `str`: Unique ID like `RESEARCHER-1`, `DATA_ANALYST-1`, etc.

**Example:**
```python
subagent_id = tracker.register_spawn("researcher", "Climate change impacts")
# Returns: "RESEARCHER-1"
```

#### `current_label(agent_type: str) -> str`

Get the display label for an agent type.

**Parameters:**
- `agent_type` (str): Agent type

**Returns:**
- `str`: Human-readable label (e.g., `RESEARCHER-1` if registered, otherwise `RESEARCHER`)

#### `record_tool_call(agent_type: str, tool_name: str, args: dict) -> None`

Record a tool call in the JSONL log.

**Parameters:**
- `agent_type` (str): Agent type making the call
- `tool_name` (str): Name of the tool
- `args` (dict): Arguments passed to the tool

**JSONL Format:**
```json
{
  "event": "tool_call",
  "agent": "RESEARCHER-1",
  "tool": "web_search",
  "args_summary": "query='climate change'",
  "ts": "2025-05-01T14:30:22.123456"
}
```

#### `close() -> None`

Close the JSONL log file. Call when done with tracking.

---

### `TranscriptWriter`

Dual-writes output to console and a transcript file.

**Location:** `src/utils/transcript.py`

#### `__init__(transcript_file: Path)`

```python
def __init__(self, transcript_file: Path):
    self._file = open(transcript_file, "w", encoding="utf-8")
```

**Parameters:**
- `transcript_file` (Path): Path to write transcript to

#### `write(text: str, end: str = "", flush: bool = True) -> None`

Write text to both console and transcript file.

**Parameters:**
- `text` (str): Text to write
- `end` (str): Suffix (default: empty, append no newline)
- `flush` (bool): Flush file immediately (default: True)

**Example:**
```python
transcript.write("Agent: ")
transcript.write(result)
transcript.write("\n")
```

#### `write_to_file(text: str) -> None`

Write text to transcript file only (not console).

**Example:**
```python
transcript.write_to_file("\nYou: Research AI safety\n")  # Logged but not echoed
```

#### `close() -> None`

Close the transcript file.

#### Context manager

`TranscriptWriter` supports the context manager protocol:

```python
with TranscriptWriter(Path("transcript.txt")) as transcript:
    transcript.write("Hello")
```

---

## Utility functions

### `setup_session() -> tuple[Path, Path]`

Create a timestamped session directory under `logs/` and return paths.

**Location:** `src/utils/transcript.py`

**Returns:**
- `(transcript_file: Path, session_dir: Path)` — Paths to transcript and session directory

**Example:**
```python
from src.utils.transcript import setup_session
transcript_file, session_dir = setup_session()
print(session_dir)  # logs/session_20250501_143022
```

---

### `make_agent_factory(on_spawn, on_tool_call, model) -> Callable[[str], AgentRunner]`

Create a factory function that produces `AgentRunner` instances for subagent types.

**Location:** `src/core/subagent_factory.py`

**Parameters:**
- `on_spawn` (Callable): Callback on subagent spawn
- `on_tool_call` (Callable): Callback on tool call
- `model` (str): Model to use for all subagents (default: `DEFAULT_MODEL`)

**Returns:**
- A callable that takes `subagent_type: str` and returns an `AgentRunner`

**Example:**
```python
from src.core.subagent_factory import make_agent_factory

def on_spawn(agent_type: str, description: str):
    print(f"Spawning {agent_type}: {description}")

def on_tool_call(agent_type: str, tool_name: str, args: dict):
    print(f"{agent_type} -> {tool_name}")

factory = make_agent_factory(on_spawn=on_spawn, on_tool_call=on_tool_call)
researcher = factory("researcher")
result = await researcher.run("Research quantum computing")
```

---

### `load_prompt(filename: str) -> str`

Load a system prompt from the `prompts/` directory.

**Location:** `src/core/subagent_factory.py`

**Parameters:**
- `filename` (str): Prompt file name (e.g., `"researcher.txt"`)

**Returns:**
- `str`: Contents of the prompt file

**Example:**
```python
from src.core.subagent_factory import load_prompt
prompt = load_prompt("lead_agent.txt")
```

---

## Tool implementations

All tools are async-friendly via `asyncio.to_thread()`. See `src/core/tools.py`.

### `web_search(query: str, max_results: int = 10) -> str`

Search the internet using DuckDuckGo.

**Parameters:**
- `query` (str): Search query
- `max_results` (int): Maximum results to return (default: 10)

**Returns:**
- `str`: Formatted search results, one per line with title, URL, and snippet

**Example:**
```python
from src.core.tools import web_search
results = await asyncio.to_thread(web_search, "machine learning trends 2025", max_results=5)
```

### `write_file(file_path: str, content: str) -> str`

Write content to a file, creating parent directories as needed.

**Parameters:**
- `file_path` (str): Destination file path
- `content` (str): Content to write

**Returns:**
- `str`: Confirmation message or error

**Example:**
```python
from src.core.tools import write_file
result = await asyncio.to_thread(write_file, "files/notes.md", "# Research Notes\n...")
```

### `read_file(file_path: str) -> str`

Read content from a file.

**Parameters:**
- `file_path` (str): File path to read

**Returns:**
- `str`: File contents or error message

**Example:**
```python
from src.core.tools import read_file
content = await asyncio.to_thread(read_file, "files/notes.md")
```

### `glob_files(pattern: str) -> str`

Find files matching a glob pattern.

**Parameters:**
- `pattern` (str): Glob pattern (e.g., `"files/**/*.md"`)

**Returns:**
- `str`: Newline-separated list of matching file paths or error

**Example:**
```python
from src.core.tools import glob_files
files = await asyncio.to_thread(glob_files, "files/research_notes/*.md")
```

### `bash_execute(command: str, timeout: int = 120) -> str`

Execute a shell command and return combined stdout/stderr.

**Parameters:**
- `command` (str): Shell command to run
- `timeout` (int): Timeout in seconds (default: 120)

**Returns:**
- `str`: Command output or error message

**Example:**
```python
from src.core.tools import bash_execute
output = await asyncio.to_thread(bash_execute, "ls -la files/")
```

---

## OpenAI API schemas

Tool schemas are defined in `src/core/schemas.py` as OpenAI-compatible function definitions.

**Available schemas:**
- `WEB_SEARCH` — web_search tool
- `WRITE_FILE` — write_file tool
- `READ_FILE` — read_file tool
- `GLOB_FILES` — glob_files tool
- `BASH_EXECUTE` — bash_execute tool
- `SPAWN_SUBAGENT` — spawn_subagent tool

**Tool availability (TOOL_SETS):**

```python
TOOL_SETS: dict[str, list] = {
    "lead": [SPAWN_SUBAGENT],
    "researcher": [WEB_SEARCH, WRITE_FILE],
    "data-analyst": [GLOB_FILES, READ_FILE, BASH_EXECUTE, WRITE_FILE],
    "report-writer": [GLOB_FILES, READ_FILE, BASH_EXECUTE, WRITE_FILE],
}
```

---

## Type hints

All async functions use standard Python type hints. Example:

```python
async def run(self, user_prompt: str) -> str:
    ...

async def _execute_tool_calls(self, tool_calls: list) -> list[dict]:
    ...
```

Requires Python 3.10+.
