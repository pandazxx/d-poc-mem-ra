"""Tool implementations for the research agent."""

import glob as _glob
import subprocess
from pathlib import Path

from ddgs import DDGS


def web_search(query: str, max_results: int = 10) -> str:
    """Search the web using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No results found for: {query}"

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', '')}")
            lines.append(f"URL: {r.get('href', '')}")
            lines.append(r.get("body", ""))
            lines.append("")
        return "\n".join(lines)
    except Exception as exc:
        return f"Search error: {exc}"


def write_file(file_path: str, content: str) -> str:
    """Write content to a file, creating parent directories as needed."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {file_path}"
    except Exception as exc:
        return f"Write error: {exc}"


def read_file(file_path: str) -> str:
    """Read content from a file."""
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as exc:
        return f"Read error: {exc}"


def glob_files(pattern: str) -> str:
    """Find files matching a glob pattern."""
    try:
        matches = _glob.glob(pattern, recursive=True)
        if not matches:
            return f"No files found matching: {pattern}"
        return "\n".join(sorted(matches))
    except Exception as exc:
        return f"Glob error: {exc}"


def bash_execute(command: str, timeout: int = 120) -> str:
    """Execute a shell command and return combined stdout/stderr."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as exc:
        return f"Bash error: {exc}"
