# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Agentic Undercover Environment (AUE)** — Multi-agent LLM simulation of the Undercover social deduction game. 4 agents (1 Imposter + 3 Villagers) play through structured rounds orchestrated by a LangGraph state machine, with real-time WebSocket streaming to a Next.js frontend.

## Commands

Use `make` for all operations: `make up`, `make test`, `make lint`, `make format`, `make migrate`. Run a single backend test with `cd apps/api && uv run pytest tests/unit/path/to/test.py::test_name -v`.

## Game Flow (LangGraph State Machine)

```
INIT → SPEAKING → DELIBERATION ↺ → POLLING → VOTING → REACTION → ENDGAME
                  ↑_____________↓ (router loops or advances)
```

- **Conditional routing**: `route_dynamic_deliberation` selects next speaker by priority (direct rebuttal → zero-turn agents → one-turn agents → random), capped at `alive_count × 4` messages. `poll_router` checks `proceed_to_vote` to either advance to VOTING or loop back to SPEAKING.
- **State**: `GameState` is a mutable Pydantic model passed by reference inside a LangGraph `TypedDict` (`GraphState`). Deliberation tracking fields (`next_speaker_id`, `deliberation_message_count`, `turns_count`) are reset on each new deliberation segment.
- **Model tiering**: REACTION and POLLING phases use `fast_llm`; all others use `smart_llm`. Groq `llama-4-scout` failures auto-fallback to `llama-3.3-70b-versatile`.

## Key Patterns

- **Structured LLM output**: Every phase has a frozen Pydantic output model (e.g., `DeliberationOutput` with `step_1_audit`, `step_2_anti_repetition`, `step_3_intent_and_target`, `public_statement`, `intent`, `target_name`). LangChain `.with_structured_output(include_raw=True)` is used for parsing.
- **Retry logic**: `invoke_with_retry` in `src/agents/retry.py` — semantic errors (ValidationError) get 1 retry with feedback message appended; network errors get 3 retries with exponential backoff via tenacity. Rate limit errors raise `RateLimitError` immediately (no retry).
- **Redis dual-use**: Pub/sub for real-time WebSocket events (`episode:{id}` channel) + list for historical catch-up (`episode_events:{id}`). Also used for quota tracking and pending episode config caching.
- **API key isolation**: 4 Groq API keys (`GROQ_API_KEY_1` through `_4`) auto-assigned round-robin to agents via `api_key_index` (1–4) in the episodes route. `get_llm_key()` in `src/core/config.py` handles key retrieval with fallback to key 1.
- **Provider support**: OpenAI, Gemini, Groq, DeepSeek — all via LangChain chat models. DeepSeek uses ChatOpenAI with `base_url="https://api.deepseek.com/v1"`.
- **Testing**: pytest with `asyncio_mode = "auto"`, tests mirror `src/` structure under `tests/unit/` and `tests/integration/`. `fakeredis` + `aiosqlite` for integration tests (no real Redis/Postgres needed).
- **Frontend state**: Zustand for setup wizard; WebSocket-driven game feed via custom `useGameStream` hook. Node.js native test runner (`node --experimental-strip-types --test`) — NOT Vitest/Jest.

## Code Style

Python `snake_case`, TypeScript `camelCase`. Ruff (line-length 88), ESLint (`eslint-config-next`). Pydantic models `frozen=True` except `GameState` (`frozen=False` — engine only). Agent IDs: `agent_0` through `agent_3`.

## Web Frontend

Next.js 16 with breaking changes — read `apps/web/AGENTS.md` and `node_modules/next/dist/docs/` before writing code. Dependencies and tooling in `apps/web/package.json`.

## Environment

Copy `.env.example` → `.env`, fill in LLM API keys. Four isolated Groq keys recommended for the 4 agents to avoid rate limits. `DATABASE_URL` and `REDIS_URL` are pre-configured for Docker Compose networking.