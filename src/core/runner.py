"""Core AgentRunner: drives the agentic tool-call loop using NVIDIA NIM LLMs."""

import asyncio
import json
import logging
import os
from typing import Callable, Optional

from openai import AsyncOpenAI

from .schemas import TOOL_SETS
from .tools import bash_execute, glob_files, read_file, web_search, write_file

logger = logging.getLogger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.1-70b-instruct"


class AgentRunner:
    """
    Runs a single agent in an agentic loop.

    - Calls the NVIDIA NIM LLM (OpenAI-compatible API).
    - Handles tool calls returned by the model.
    - Supports concurrent subagent spawning when the lead agent issues
      multiple spawn_subagent calls in one turn.
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools or None,
                tool_choice="auto" if self.tools else None,
                temperature=0.6,
                top_p=0.95,
                max_tokens=4096,
            )

            choice = response.choices[0]
            msg = choice.message

            # Append assistant turn to history in the dict format the API expects.
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

            # Execute all tool calls (spawn_subagent calls run concurrently).
            tool_results = await self._execute_tool_calls(msg.tool_calls)
            self.messages.extend(tool_results)

    async def _execute_tool_calls(self, tool_calls: list) -> list[dict]:
        """Execute all tool calls concurrently and return tool result messages."""
        tasks = [self._execute_one(tc) for tc in tool_calls]
        return list(await asyncio.gather(*tasks))

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
        if name == "spawn_subagent":
            return await self._spawn(
                args["subagent_type"], args["description"], args["prompt"]
            )
        return f"Unknown tool: {name}"

    async def _spawn(self, subagent_type: str, description: str, prompt: str) -> str:
        if not self.agent_factory:
            return "Cannot spawn subagent: no factory configured"

        if self.on_spawn:
            self.on_spawn(subagent_type, description)

        runner: AgentRunner = self.agent_factory(subagent_type)
        result = await runner.run(prompt)
        return f"[{subagent_type} completed]\n{result}"
