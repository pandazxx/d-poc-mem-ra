"""Tracks subagent spawns and tool calls; writes structured logs."""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SubagentTracker:
    """
    Lightweight tracker that:
    - Assigns human-readable IDs to each spawned subagent (RESEARCHER-1, etc.)
    - Logs tool calls to console via the transcript writer
    - Writes structured JSONL entries to <session_dir>/tool_calls.jsonl
    """

    def __init__(
        self,
        transcript_writer=None,
        session_dir: Optional[Path] = None,
    ):
        self._counters: dict[str, int] = defaultdict(int)
        self._active: dict[str, str] = {}  # agent_type -> current subagent_id
        self.transcript_writer = transcript_writer
        self._log_file = None
        if session_dir:
            self._log_file = open(session_dir / "tool_calls.jsonl", "w", encoding="utf-8")

    def register_spawn(self, subagent_type: str, description: str) -> str:
        """Register a new subagent spawn and return its unique ID."""
        self._counters[subagent_type] += 1
        subagent_id = f"{subagent_type.upper().replace('-', '_')}-{self._counters[subagent_type]}"
        self._active[subagent_type] = subagent_id
        self._jsonl({
            "event": "spawn",
            "subagent_id": subagent_id,
            "subagent_type": subagent_type,
            "description": description,
        })
        return subagent_id

    def current_label(self, agent_type: str) -> str:
        """Return the display label for the given agent type."""
        return self._active.get(agent_type, agent_type.upper())

    def record_tool_call(self, agent_type: str, tool_name: str, args: dict) -> None:
        label = self.current_label(agent_type)
        self._jsonl({
            "event": "tool_call",
            "agent": label,
            "tool": tool_name,
            "args_summary": _summarise(args),
        })

    def close(self) -> None:
        if self._log_file:
            self._log_file.close()

    def _jsonl(self, entry: dict) -> None:
        if not self._log_file:
            return
        entry["ts"] = datetime.now().isoformat()
        self._log_file.write(json.dumps(entry) + "\n")
        self._log_file.flush()


def _summarise(args: dict, limit: int = 120) -> str:
    if "query" in args:
        q = args["query"]
        return f"query={q[:limit]!r}" if len(q) <= limit else f"query={q[:limit]!r}..."
    if "file_path" in args and "content" in args:
        return f"file={Path(args['file_path']).name!r} ({len(args['content'])} chars)"
    if "file_path" in args:
        return f"path={args['file_path']!r}"
    if "pattern" in args:
        return f"pattern={args['pattern']!r}"
    if "subagent_type" in args:
        return f"spawn={args['subagent_type']!r} ({args.get('description', '')})"
    return str(args)[:limit]
