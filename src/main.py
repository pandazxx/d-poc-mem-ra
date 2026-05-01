"""Entry point for the NVIDIA research agent."""

import asyncio
import os
import textwrap

from dotenv import load_dotenv

from .core.runner import AgentRunner, DEFAULT_MODEL, NVIDIA_BASE_URL
from .core.subagent_factory import _inject_files_dir, load_prompt, make_agent_factory
from .utils.tracker import SubagentTracker
from .utils.transcript import TranscriptWriter, setup_session

# Max chars to show inline for tool results and prompts in the transcript.
_RESULT_PREVIEW = 300
_PROMPT_PREVIEW = 400


def _wrap(text: str, indent: str = "    ") -> str:
    """Wrap long text for readable transcript display."""
    return textwrap.fill(text, width=100, initial_indent=indent, subsequent_indent=indent)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"… [{len(text) - limit} more chars]"


def _fmt_args(tool_name: str, args: dict) -> str:
    """Format tool arguments as compact key=value lines."""
    lines = []
    for k, v in args.items():
        v_str = str(v)
        if tool_name == "spawn_subagents" and k == "subagents":
            # Handled separately in on_spawn
            continue
        if len(v_str) > 120:
            v_str = v_str[:120] + "…"
        lines.append(f"    {k}: {v_str}")
    return "\n".join(lines)


def main() -> None:
    load_dotenv()
    asyncio.run(_chat())


async def _chat() -> None:
    if not os.environ.get("NVIDIA_API_KEY"):
        print("\nError: NVIDIA_API_KEY not found.")
        print("Set it in a .env file or export NVIDIA_API_KEY in your shell.")
        print("Get your key at: https://build.nvidia.com\n")
        return

    transcript_file, session_dir = setup_session()
    # Each session writes its files into its own subdirectory so sessions never
    # contaminate each other.
    session_files_dir = str(session_dir / "files")
    transcript = TranscriptWriter(transcript_file)
    tracker = SubagentTracker(transcript_writer=transcript, session_dir=session_dir)

    # ── callbacks ──────────────────────────────────────────────────────────────

    def on_agent_text(agent_type: str, text: str) -> None:
        """Agent produced reasoning/planning text between tool calls."""
        label = tracker.current_label(agent_type)
        snippet = _truncate(text.strip(), _RESULT_PREVIEW)
        transcript.write(f"\n[{label}] says: {snippet}")

    def on_spawn(subagent_type: str, description: str, prompt: str) -> None:
        """Lead agent is about to spawn a subagent."""
        subagent_id = tracker.register_spawn(subagent_type, description)
        prompt_preview = _truncate(prompt.strip(), _PROMPT_PREVIEW)
        transcript.write(
            f"\n\n{'─'*60}"
            f"\n[Spawning {subagent_id}]  {description}"
            f"\n  type   : {subagent_type}"
            f"\n  prompt : {prompt_preview}"
            f"\n{'─'*60}"
        )

    def on_tool_call(agent_type: str, tool_name: str, args: dict) -> None:
        """Agent is about to call a tool."""
        tracker.record_tool_call(agent_type, tool_name, args)
        label = tracker.current_label(agent_type)
        arg_lines = _fmt_args(tool_name, args)
        header = f"\n[{label}] -> {tool_name}"
        transcript.write(header + (f"\n{arg_lines}" if arg_lines else ""))

    def on_tool_result(agent_type: str, tool_name: str, args: dict, result: str) -> None:
        """Tool finished — log the result."""
        label = tracker.current_label(agent_type)
        preview = _truncate(result.strip(), _RESULT_PREVIEW)
        # Write result to transcript file only (keeps console less noisy).
        transcript.write_to_file(f"\n    => {preview}\n")
        tracker.record_tool_result(agent_type, tool_name, result)

    # ── agent setup ────────────────────────────────────────────────────────────

    factory = make_agent_factory(
        files_dir=session_files_dir,
        on_spawn=on_spawn,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        on_agent_text=on_agent_text,
    )
    lead_system_prompt = _inject_files_dir(load_prompt("lead_agent.txt"), session_files_dir)
    lead_runner = AgentRunner(
        system_prompt=lead_system_prompt,
        agent_type="lead",
        model=DEFAULT_MODEL,
        agent_factory=factory,
        on_spawn=on_spawn,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        on_agent_text=on_agent_text,
    )

    # ── banner ─────────────────────────────────────────────────────────────────

    print("\n" + "=" * 60)
    print("  NVIDIA NIM Research Agent")
    print("=" * 60)
    print(f"\nModel : {DEFAULT_MODEL}")
    print(f"API   : {NVIDIA_BASE_URL}")
    print("\nTo change the model set NVIDIA_MODEL=<id> in .env")
    print("To list available models: uv run python -m src.list_models")
    print("\nResearch any topic and get a comprehensive PDF")
    print("report with data visualizations.")
    print("\nType 'exit' to quit.\n")

    # ── main loop ──────────────────────────────────────────────────────────────

    try:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input or user_input.lower() in {"exit", "quit", "q"}:
                break

            transcript.write(f"\n{'='*60}\nYou: {user_input}\n{'='*60}")
            transcript.write("\nAgent: ")

            try:
                result = await lead_runner.run(user_input)
            except Exception as exc:
                result = f"[Error: {exc}]"

            transcript.write(f"\n{result}\n")
            lead_runner.messages = []
    finally:
        transcript.write("\n\nGoodbye!\n")
        transcript.close()
        tracker.close()
        print(f"\nSession logs: {session_dir}")
        print(f"  transcript : {transcript_file}")
        print(f"  tool calls : {session_dir / 'tool_calls.jsonl'}")
        print(f"  files      : {session_files_dir}/")


if __name__ == "__main__":
    main()
