# 🏛️ Architecture Specification

**Document:** `ARCHITECTURE.md`
**Project:** Agentic Undercover Environment (AUE)
**Version:** 2.0.0 (Production Setup)
**Status:** DRAFT — Evolved to Microservices Architecture (2026-06-30)

> This document outlines the system architecture, technology stack, directory structure, and deployment strategy for AUE. The project has evolved from a simple terminal script to a production-grade, real-time web application.

---

## 1. System Overview

AUE is built as a **Dockerized Microservices Application**. It separates the web client, the game engine (AI processing), real-time state management, and persistent storage.

```mermaid
graph TD
    Client[Web Browser]
    
    subgraph Frontend Service [Next.js Container]
        UI[UI Components]
        WSClient[WebSocket Client]
    end
    
    subgraph Backend Service [FastAPI Container]
        API[REST API]
        WSServer[WebSocket Server]
        Engine[LangGraph Engine]
        Agents[LangChain Agents]
    end
    
    subgraph State & Storage
        Redis[(Redis)]
        Postgres[(PostgreSQL)]
    end
    
    LLMs((LLM Providers API))
    
    Client <-->|HTTP / WS| Frontend Service
    UI --> API
    WSClient <--> WSServer
    API --> Postgres
    Engine <--> Redis
    WSServer <--> Redis
    Engine <--> Postgres
    Agents <--> LLMs
```

---

## 2. Technology Stack

### 2.1 Frontend Service (`/apps/web`)
*   **Framework:** Next.js 16 (App Router), React
*   **Language:** TypeScript
*   **Styling:** Tailwind CSS 4 + Framer Motion
*   **Communication:** HTTP REST (setup/config) + WebSocket (real-time game stream)
*   **State Management:** Zustand stores — `useSetupStore` (wizard) + `useGameStore` (event stream)
*   **Testing:** Node.js native test runner (`--experimental-strip-types`)

### 2.2 Backend Service (`/apps/api`)
*   **Framework:** FastAPI (Python 3.11+)
*   **Dependency Management:** `uv` (`uv sync --frozen`)
*   **Orchestration:** LangGraph — 7-node `StateGraph`
  (INIT → SPEAKING → DELIBERATION ↺ → POLLING → VOTING → REACTION → ENDGAME)
  with **2 conditional routers**:
  - `route_dynamic_deliberation` (priority-based speaker selection)
  - `poll_router` (threshold check to advance to voting or loop back)
*   **LLM Integration:** LangChain provider-agnostic wrappers
  (`langchain-openai`, `langchain-google-genai`, `langchain-groq`)
  with dual-model tiering per agent (smart / fast).
*   **Data Validation:** Pydantic v2 — `frozen=True` outputs,
  `model_validator(mode="after")` for intent/target_name enforcement,
  `include_raw=True` for token-usage extraction
*   **Real-time Protocol:** WebSocket endpoint + Redis pub/sub
  - Events published to `episode:{id}` channel
  - Historical catch-up via Redis list `episode_events:{id}`
*   **Retry logic:** `invoke_with_retry` — 1 semantic retry, 3 network
  retries (exponential), zero retries for rate limits (provider quota
  exhausted immediately), Groq Scout → llama-3.3 fallback

### 2.3 Data Layer
*   **Ephemeral State & Pub/Sub:** Redis
    *   *Purpose:* Real-time message brokering for WebSockets. When the LangGraph engine generates an agent's response, it publishes to Redis. The WebSocket server subscribes to Redis and pushes updates to the frontend.
*   **Persistent Storage:** PostgreSQL + SQLAlchemy (Async)
    *   *Purpose:* Storing historical match data, action logs, and aggregated statistics (win rates, tokens used).

### 2.4 Infrastructure
*   **Containerization:** Docker & Docker Compose
*   **Entry Point:** Single `docker-compose.yml` to spin up all 4 services (Next.js, FastAPI, Redis, Postgres).

---

## 3. Communication Patterns

### 3.1 Pre-Game (REST API + React Wizard)
1. User walks through the 3-step setup wizard in Next.js:
   - Step 1: Game parameters (topic, secret word, max rounds)
   - Step 2: Per-agent provider/model configuration with live API-key monitor
   - Step 3: Review & Launch → `POST /api/episodes` with `EpisodeConfig`
2. Backend creates the episode record, returns an `episode_id`.
3. Frontend navigates to `/game/{episode_id}` and opens the WebSocket stream.

### 3.2 In-Game (WebSockets + Redis Pub/Sub)
1. Frontend connects to `ws://api/ws/episodes/{episode_id}/stream`.
2. Frontend sends `"START"` over WS.
3. The `EpisodeRunner.run()` kicks off the LangGraph state machine in a
   `asyncio.create_task` (background).
4. Each node emits game events via `EventEmitter` → Redis pub/sub:
   - `GAME_START`, `ROUND_STARTED`, `AGENT_SPOKE`, `AGENT_DELIBERATED`
   - `POLLING_STARTED`, `POLL_RESULT`, `VOTING_STARTED`, `VOTE_CAST`
   - `ELIMINATION_RESULT`, `LAST_WORDS`, `ROLE_REVEAL`, `SURVIVOR_REACTED`
   - `GAME_OVER`, `GAME_ERROR` (rate-limit / unexpected crash)
5. The WebSocket endpoint reads from Redis pub/sub and pushes events to the
   frontend; historical catch-up is done via Redis list `episode_events:{id}`.

### 3.3 Post-Game
1. Upon reaching `endgame_node`, the engine builds the `EpisodeExport`
   (all action logs, messages, votes).
2. The export is persisted to PostgreSQL via `EpisodeRepository.create()`.
3. Final events are emitted over the WebSocket stream.
4. Action logs include: prompt context, raw LLM response, structured output,
   token counts, latency per call. Note: prompt context currently stores a
   stub placeholder (`{"stub": "false"}`) — full prompt capture is deferred
   (E4-T2).

---

## 4. Directory Structure (Monorepo)

```text
agentic-undercover-env/
├── docker-compose.yml        # Main entry point to run everything
├── Makefile                  # Helper commands (make up, make down, make dev)
│
├── apps/
│   ├── web/                  # Next.js 16 Frontend
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── setup/    # SetupWizard, 3-step form cards
│   │   │   │   ├── game/     # ChatFeed, AgentMessage, VoteReveal, …
│   │   │   │   ├── ui/       # Button, Card, Input, Select, Badge
│   │   │   │   └── layout/   # AppShell
│   │   │   ├── lib/          # Store, useGameStream (WebSocket), types, constants
│   │   │   ├── store/        # Zustand setup-wizard state
│   │   │   └── types/        # Event TS types
│   │   └── src/__tests__/
│   │
│   └── api/                  # FastAPI Backend
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── src/
│       │   ├── main.py       # Mounts api_router / ws_router
│       │   ├── core/         # Config, Redis client, quota tracking
│       │   ├── models/       # Pydantic: enums, configs, outputs, state, export, …
│       │   ├── db/           # SQLAlchemy async models + Alembic migrations
│       │   ├── engine/       # LangGraph nodes, graph builder, dynamic routers
│       │   ├── agents/       # AIAgent, BaseAgent ABC, HumanAgent stub,
│       │   │                 #   prompt_templates, prompt_builder, retry, llm_factory
│       │   ├── api/          # REST routes: episodes, providers, quota
│       │   └── api/ws/       # WebSocket endpoint: game_stream per-episode
│       └── tests/            # pytest: unit/ mirror src/ + integration/
│
└── docs/                     # Project Documentation
    ├── PRD.md
    ├── GAME_RULES_SPEC.md
    ├── DATA_SCHEMA.md
    ├── ARCHITECTURE.md
    └── AGENT_DESIGN.md
```

---

## 5. Development Workflow & Testing

### 5.1 Local Setup
To bring up the entire stack locally:
```bash
docker-compose up --build
```
This starts:
- `postgres` on port 5432
- `redis` on port 6379
- `api` (FastAPI) on port 8000
- `web` (Next.js) on port 3000

### 5.2 Backend Testing Strategy
- **Unit Tests:** Isolated node/router/output tests using `MockAgent`
  (test double from `tests/unit/engine/conftest.py` that returns
  pre-configured Pydantic outputs per phase, with `StopIteration` safe
  defaults). `fakeredis` for Redis-using tests.
- **Integration Tests:** Full linear pipeline test (`test_runner.py`)
  runs the complete LangGraph graph with `MockAgent` injects,
  `fakeredis` for pub/sub verification, and `aiosqlite`/mock DB session
  — no real Redis/Postgres needed. Verifies event count, sequence,
  rate-limit error handling, and quota exhaustion.
- **Evaluation Scripts:** Deferred to Sprint 3 — 100+ episode batch runs
  using cheap/fast models to measure Imposter win rates and prompt quality.

---

## 6. Security & Safety

- **API Keys:** Never hardcoded. Managed via `.env` files parsed by
  `pydantic-settings` on the backend. 4 isolated Groq keys loaded
  round-robin per agent (API keys 1–4 → agents 0–3).
- **Rate Limiting:** `invoke_with_retry` (see §2.2) retries network
  errors 3× (exponential) but propagates rate limits immediately so the
  episode can be aborted + provider marked exhausted in quota tracker.
- **Frontend Secret Protection:** The Next.js client never touches LLM API
  keys; all LLM calls are strictly server-side.
