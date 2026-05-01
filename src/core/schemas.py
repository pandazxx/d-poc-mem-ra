"""OpenAI-compatible tool schemas for each agent type."""

WEB_SEARCH = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the internet for information on any topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
}

WRITE_FILE = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file. Creates parent directories as needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Destination path"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["file_path", "content"],
        },
    },
}

READ_FILE = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read content from a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to read"},
            },
            "required": ["file_path"],
        },
    },
}

GLOB_FILES = {
    "type": "function",
    "function": {
        "name": "glob_files",
        "description": "Find files matching a glob pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern, e.g. files/research_notes/*.md",
                },
            },
            "required": ["pattern"],
        },
    },
}

BASH_EXECUTE = {
    "type": "function",
    "function": {
        "name": "bash_execute",
        "description": "Execute a shell command and return its output.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
            },
            "required": ["command"],
        },
    },
}

SPAWN_SUBAGENTS = {
    "type": "function",
    "function": {
        "name": "spawn_subagents",
        "description": (
            "Spawn one or more specialized subagents. All items in the list run concurrently. "
            "Use a single call with multiple items to parallelize researchers. "
            "Available types: researcher, data-analyst, report-writer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "subagents": {
                    "type": "array",
                    "description": "List of subagents to spawn (all run in parallel).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "subagent_type": {
                                "type": "string",
                                "enum": ["researcher", "data-analyst", "report-writer"],
                                "description": "Type of subagent",
                            },
                            "description": {
                                "type": "string",
                                "description": "Brief 3-5 word description of the task",
                            },
                            "prompt": {
                                "type": "string",
                                "description": "Detailed instructions for the subagent",
                            },
                        },
                        "required": ["subagent_type", "description", "prompt"],
                    },
                },
            },
            "required": ["subagents"],
        },
    },
}

# Tool sets per agent type
TOOL_SETS: dict[str, list] = {
    "lead": [SPAWN_SUBAGENTS],
    "researcher": [WEB_SEARCH, WRITE_FILE],
    "data-analyst": [GLOB_FILES, READ_FILE, BASH_EXECUTE, WRITE_FILE],
    "report-writer": [GLOB_FILES, READ_FILE, BASH_EXECUTE, WRITE_FILE],
}
