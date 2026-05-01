"""Factory for creating specialized subagent runners."""

from pathlib import Path
from typing import Callable, Optional

from .runner import AgentRunner, DEFAULT_MODEL

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


def _inject_files_dir(prompt: str, files_dir: str) -> str:
    """Replace the generic 'files/<subdir>' prefixes with the session-specific path.

    Also replaces the standalone 'files' argument in the generate_pdf.py command.
    """
    for subdir in ("research_notes", "charts", "data", "reports"):
        prompt = prompt.replace(f"files/{subdir}", f"{files_dir}/{subdir}")
    # Replace the script argument: generate_pdf.py files → generate_pdf.py <session_dir>
    prompt = prompt.replace(
        "generate_pdf.py files",
        f"generate_pdf.py {files_dir}",
    )
    return prompt


def make_agent_factory(
    files_dir: str = "files",
    on_spawn: Optional[Callable] = None,
    on_tool_call: Optional[Callable] = None,
    on_tool_result: Optional[Callable] = None,
    on_agent_text: Optional[Callable] = None,
    model: str = DEFAULT_MODEL,
) -> Callable[[str], AgentRunner]:
    """Return a callable that produces an AgentRunner for the given subagent type."""

    prompts = {
        "researcher": _inject_files_dir(load_prompt("researcher.txt"), files_dir),
        "data-analyst": _inject_files_dir(load_prompt("data_analyst.txt"), files_dir),
        "report-writer": _inject_files_dir(load_prompt("report_writer.txt"), files_dir),
    }

    def factory(subagent_type: str) -> AgentRunner:
        system_prompt = prompts.get(subagent_type, f"You are a {subagent_type} agent.")
        return AgentRunner(
            system_prompt=system_prompt,
            agent_type=subagent_type,
            model=model,
            agent_factory=factory,
            on_spawn=on_spawn,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
            on_agent_text=on_agent_text,
        )

    return factory
