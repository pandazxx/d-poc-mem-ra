"""List all LLM models available on your NVIDIA NIM account.

Usage:
    uv run python -m src.list_models
"""

import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from .core.runner import NVIDIA_BASE_URL

# Models known to support parallel (multi) tool calls on NVIDIA NIM.
# Update this list as NVIDIA expands support.
PARALLEL_TOOL_CALL_MODELS = {
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-405b-instruct",
    "mistralai/mistral-large-2-instruct",
    "mistralai/mixtral-8x22b-instruct-v0.1",
    "nvidia/llama-3.1-nemotron-70b-instruct",
}


async def _list() -> None:
    load_dotenv()
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        print("Error: NVIDIA_API_KEY not set.")
        return

    client = AsyncOpenAI(base_url=NVIDIA_BASE_URL, api_key=key)
    models = await client.models.list()

    ids = sorted(m.id for m in models.data)
    print(f"\n{'Model ID':<55} {'Parallel tool calls'}")
    print("-" * 75)
    for mid in ids:
        flag = "✓" if mid in PARALLEL_TOOL_CALL_MODELS else ""
        print(f"{mid:<55} {flag}")

    print(f"\nTotal: {len(ids)} models")
    print("\nModels marked ✓ are known to support multi-tool-calls per response.")
    print("Set NVIDIA_MODEL=<id> in your .env to select one.\n")


def main() -> None:
    asyncio.run(_list())


if __name__ == "__main__":
    main()
