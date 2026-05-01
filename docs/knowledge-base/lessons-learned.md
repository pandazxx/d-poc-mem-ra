# Lessons Learned

A record of architectural decisions, discoveries, and troubleshooting outcomes from building the NVIDIA NIM Research Agent.

---

## 2025-05-01: Core architectural decisions

**Date:** 2025-05-01

**Summary:**
Initial build of NVIDIA NIM Research Agent using OpenAI SDK, DuckDuckGo search, asyncio-based concurrent spawning, and OpenAI-compatible message history format for the Nvidia API.

**Root cause / Context:**
The project is a rewrite of the Anthropic claude-agent-sdk-demos research-agent without the Claude Agent SDK. Design decisions were driven by:
1. Need to work with NVIDIA NIM's OpenAI-compatible API
2. Goal of achieving parallel subagent execution matching the original SDK's Task-based concurrency
3. Requirement to support web search without API keys
4. Need to generate reports with embedded visualizations

**Fix applied:**

### Decision 1: Use OpenAI SDK for NVIDIA NIM API

- **Rationale:** NVIDIA NIM exposes an OpenAI-compatible API endpoint (`https://integrate.api.nvidia.com/v1`). The OpenAI Python SDK (`openai>=1.0.0`) provides a well-tested, stable client that works out-of-the-box with any OpenAI-compatible endpoint via `base_url` parameter.
- **Alternative considered:** Custom HTTP client or requests library. Rejected because it would require reimplementing authentication, retry logic, streaming, and tool-call serialization.
- **Implementation:** `src/core/runner.py` creates an `AsyncOpenAI` client pointed at the NVIDIA endpoint:
  ```python
  client = AsyncOpenAI(
      base_url="https://integrate.api.nvidia.com/v1",
      api_key=os.environ["NVIDIA_API_KEY"],
  )
  ```
- **Tradeoff:** Tight coupling to OpenAI SDK (but minimal risk; any future OpenAI-compatible provider requires only endpoint swap).

### Decision 2: Use DuckDuckGo for web search

- **Rationale:** DuckDuckGo's `duckduckgo-search` library requires no API key, making the system immediately accessible without additional setup. Avoids Bing/Google costs and quota issues.
- **Alternative considered:** Bing Web Search API, Google Custom Search API. Rejected due to cost and setup friction.
- **Implementation:** `src/core/tools.py` wraps `DDGS().text()` in a `web_search()` function.
- **Tradeoff:** Results are less curated than commercial APIs and may be slower; acceptable for research prototyping.

### Decision 3: asyncio.gather for concurrent subagent spawning

- **Rationale:** The original Anthropic SDK spawns multiple researcher agents in parallel using Task-based concurrency. Python's `asyncio.gather()` directly maps to this model: multiple `spawn_subagent` tool calls in one LLM turn are collected and executed concurrently in `_execute_tool_calls()`.
- **Alternative considered:** Sequential execution (one spawn per turn). Rejected because it defeats the core benefit of parallel research (research would take 2–4x longer for 2–4 researchers).
- **Implementation:** `src/core/runner.py` `_execute_tool_calls()` uses `asyncio.gather(*tasks)` to run all tool calls (including nested subagent spawns) concurrently.
- **Tradeoff:** Requires careful message history management to ensure tool results are appended in the same order as results arrive; handled correctly in current code.

### Decision 4: OpenAI-compatible message history format

- **Rationale:** NVIDIA NIM's API expects standard OpenAI message format with tool calls serialized as:
  ```json
  {
    "role": "assistant",
    "content": "...",
    "tool_calls": [
      {
        "id": "call_123",
        "type": "function",
        "function": {"name": "web_search", "arguments": "{...}"}
      }
    ]
  }
  ```
- **Quirk discovered:** The OpenAI SDK's `Message` object returns `tool_calls` as a list of `ToolCall` objects with nested `function` attributes. When re-sending to the API, these must be manually serialized back to the dict format shown above (JSON strings cannot be used directly for `arguments`). This is handled in `AgentRunner.run()`:
  ```python
  assistant_dict["tool_calls"] = [
      {
          "id": tc.id,
          "type": "function",
          "function": {
              "name": tc.function.name,
              "arguments": tc.function.arguments,  # Already a JSON string
          },
      }
      for tc in msg.tool_calls
  ]
  ```
- **Tradeoff:** Manual serialization is error-prone; mitigated by test coverage (future work).

## Prevention

To prevent regressions or design conflicts in future work:

1. **If integrating a new LLM provider:** Verify it supports OpenAI-compatible API format or use a dedicated client; do not mix APIs.
2. **If optimizing search:** Profile DuckDuckGo latency vs. result quality; consider caching or rate-limiting if search volume grows.
3. **If adding concurrency guarantees:** Test that message history ordering is preserved under high concurrency (many simultaneous subagent spawns).
4. **If refactoring message serialization:** Add unit tests covering tool-call round-trip (dict → OpenAI SDK → dict).

---
