"""Entry point for the NVIDIA research agent."""

import asyncio
import os

from dotenv import load_dotenv

from .core.runner import AgentRunner, DEFAULT_MODEL
from .core.subagent_factory import load_prompt, make_agent_factory
from .utils.tracker import SubagentTracker
from .utils.transcript import TranscriptWriter, setup_session


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
    transcript = TranscriptWriter(transcript_file)
    tracker = SubagentTracker(transcript_writer=transcript, session_dir=session_dir)

    def on_spawn(subagent_type: str, description: str) -> None:
        subagent_id = tracker.register_spawn(subagent_type, description)
        transcript.write(f"\n[Spawning {subagent_id}: {description}]")

    def on_tool_call(agent_type: str, tool_name: str, args: dict) -> None:
        tracker.record_tool_call(agent_type, tool_name, args)
        label = tracker.current_label(agent_type)
        transcript.write(f"\n[{label}] -> {tool_name}")

    factory = make_agent_factory(on_spawn=on_spawn, on_tool_call=on_tool_call)
    lead_runner = AgentRunner(
        system_prompt=load_prompt("lead_agent.txt"),
        agent_type="lead",
        model=DEFAULT_MODEL,
        agent_factory=factory,
        on_spawn=on_spawn,
        on_tool_call=on_tool_call,
    )

    print("\n" + "=" * 50)
    print("  NVIDIA NIM Research Agent")
    print("=" * 50)
    print(f"\nModel: {DEFAULT_MODEL}")
    print("\nResearch any topic and get a comprehensive PDF")
    print("report with data visualizations.")
    print("\nType 'exit' to quit.\n")

    try:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input or user_input.lower() in {"exit", "quit", "q"}:
                break

            transcript.write_to_file(f"\nYou: {user_input}\n")
            transcript.write("\nAgent: ")

            try:
                result = await lead_runner.run(user_input)
            except Exception as exc:
                result = f"[Error: {exc}]"

            transcript.write(result)
            transcript.write("\n")

            # Reset conversation for the next independent research query.
            lead_runner.messages = []
    finally:
        transcript.write("\n\nGoodbye!\n")
        transcript.close()
        tracker.close()
        print(f"\nSession logs: {session_dir}")
        print(f"  transcript : {transcript_file}")
        print(f"  tool calls : {session_dir / 'tool_calls.jsonl'}")


if __name__ == "__main__":
    main()
