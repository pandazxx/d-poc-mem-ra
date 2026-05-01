"""Core AgentRunner: drives the agentic tool-call loop using NVIDIA NIM LLMs."""

import asyncio
import json
import logging
import os
import random
from typing import Callable, Optional

import openai
from openai import AsyncOpenAI

from .schemas import TOOL_SETS
from .tools import bash_execute, glob_files, read_file, web_search, write_file

logger = logging.getLogger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Fallback model known to support parallel (multi) tool calls.
# Override at runtime with the NVIDIA_MODEL environment variable.
DEFAULT_MODEL = os.environ.get(
    "NVIDIA_MODEL",
    "meta/llama-3.3-70b-instruct",
)

_RETRY_MAX = 6        # max retry attempts on 429
_RETRY_BASE = 2.0     # initial backoff seconds (doubles each attempt, capped at 60s)


class AgentRunner:
    """
    Runs a single agent in an agentic loop.

    - Calls the NVIDIA NIM LLM (OpenAI-compatible API).
    - Retries with exponential backoff on 429 rate-limit responses.
    - Executes multiple tool calls concurrently (parallel tool calls).
    - Supports recursive subagent spawning via spawn_subagents.
    """

    def __init__(
        self,
        system_prompt: str,
        agent_type: str,
        model: str = DEFAULT_MODEL,
        agent_factory: Optional[Callable[["str"], "AgentRunner"]] = None,
        on_spawn: Optional[Callable[[str, str], None]] = None,
        on_tool_call: Optional[Callable[[str, str, dict], None]] = None,
    ):
        self.system_prompt = system_prompt
        self.agent_type = agent_type
        self.model = model
        self.agent_factory = agent_factory
        self.on_spawn = on_spawn
        self.on_tool_call = on_tool_call

        self.client = AsyncOpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=os.environ["NVIDIA_API_KEY"],
        )
        self.tools = TOOL_SETS.get(agent_type, [])
        self.messages: list[dict] = []

    async def run(self, user_prompt: str) -> str:
        """Run the agent on a prompt until it produces a final text response."""
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        while True:
            response = await self._call_llm()

            choice = response.choices[0]
            msg = choice.message

            assistant_dict: dict = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                assistant_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            self.messages.append(assistant_dict)

            if not msg.tool_calls:
                return msg.content or ""

            tool_results = await self._execute_tool_calls(msg.tool_calls)
            self.messages.extend(tool_results)

    async def _call_llm(self):
        """Call the LLM API with exponential backoff retry on 429."""
        delay = _RETRY_BASE
        for attempt in range(_RETRY_MAX):
            try:
                return await self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools or None,
                    tool_choice="auto" if self.tools else None,
                    temperature=0.6,
                    top_p=0.95,
                    max_tokens=4096,
                )
            except openai.NotFoundError:
                raise RuntimeError(
                    f"Model '{self.model}' not found on your NVIDIA NIM account.\n"
                    "Run  uv run python -m src.list_models  to see available models,\n"
                    "then set  NVIDIA_MODEL=<id>  in your .env file."
                ) from None
            except openai.RateLimitError:
                if attempt == _RETRY_MAX - 1:
                    raise
                # Add jitter to spread retries from concurrent subagents.
                wait = delay + random.uniform(0, delay * 0.5)
                logger.warning(
                    "[%s] 429 rate-limited (attempt %d/%d) — retrying in %.1fs",
                    self.agent_type, attempt + 1, _RETRY_MAX, wait,
                )
                print(
                    f"\n[{self.agent_type}] Rate limited, retrying in {wait:.0f}s…",
                    flush=True,
                )
                await asyncio.sleep(wait)
                delay = min(delay * 2, 300)

    async def _execute_tool_calls(self, tool_calls: list) -> list[dict]:
        """Execute all tool calls concurrently and return tool result messages."""
        return list(await asyncio.gather(*[self._execute_one(tc) for tc in tool_calls]))

    async def _execute_one(self, tool_call) -> dict:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, ValueError):
            args = {}

        if self.on_tool_call:
            self.on_tool_call(self.agent_type, name, args)

        content = await self._dispatch(name, args)
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": content,
        }

    async def _dispatch(self, name: str, args: dict) -> str:
        if name == "web_search":
            return await asyncio.to_thread(
                web_search, args["query"], args.get("max_results", 10)
            )
        if name == "write_file":
            return await asyncio.to_thread(
                write_file, args["file_path"], args["content"]
            )
        if name == "read_file":
            return await asyncio.to_thread(read_file, args["file_path"])
        if name == "glob_files":
            return await asyncio.to_thread(glob_files, args["pattern"])
        if name == "bash_execute":
            return await asyncio.to_thread(bash_execute, args["command"])
        if name == "spawn_subagents":
            specs = args.get("subagents", [])
            results = await asyncio.gather(
                *[self._spawn(s["subagent_type"], s["description"], s["prompt"]) for s in specs]
            )
            return "\n\n".join(results)
        return f"Unknown tool: {name}"

    async def _spawn(self, subagent_type: str, description: str, prompt: str) -> str:
        if not self.agent_factory:
            return "Cannot spawn subagent: no factory configured"
        if self.on_spawn:
            self.on_spawn(subagent_type, description)
        runner: AgentRunner = self.agent_factory(subagent_type)
        result = await runner.run(prompt)
        return f"[{subagent_type} completed]\n{result}"
