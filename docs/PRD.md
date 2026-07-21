# 📄 Product Requirements Document (PRD)

**Project Name:** Agentic Undercover Environment (AUE)
**Repository:** `agentic-undercover-env`
**Version:** 1.1.0
**Role:** AI Engineer & Tech Lead (You) / PM & Mentor (AI)
**Status:** DRAFT — Updated after initial Q&A alignment session (2026-06-29)

---

## 1. Executive Summary

The **Agentic Undercover Environment (AUE)** is a local-first multi-agent simulation framework based on the social deduction game mechanics of *Undercover / Spyfall*. Unlike a traditional game, AUE is a **Behavioral Laboratory** and **Evaluation Benchmark** — its purpose is to observe, measure, and log the capabilities of Large Language Models (LLMs) in:

- **Semantic deception** — Can an Imposter speak ambiguously without being detected?
- **Pragmatic inference** — Can Villagers read between the lines to identify the Imposter?
- **Deductive reasoning under asymmetric information** — Can agents update their suspicions based on evolving conversation?

The system is designed to run entirely via **cloud LLM APIs** (no local models), with a pre-game configuration UI that lets the operator tune providers, models, and player composition before each simulation episode.

---

## 2. Objectives & Success Metrics

### 🎯 Primary Goals

- **Cyclical State Machine:** Build a robust game loop (Speaking → Deliberation → Polling → Voting → Reaction) using `langgraph`.
- **Dual-Stream Cognitive Modeling:** Capture the agent's `inner_thought` (private scratchpad) separately from `public_statement` (what others see) via structured Pydantic outputs.
- **Asymmetric Provider Testing:** Allow different agents to use different LLM providers/models within the same game episode to compare strategic depth.
- **Data Persistence:** Log full game states and chat histories as timestamped JSON for future analysis and prompt optimization.

### 📈 Success Metrics for MVP (Sprint 1)

- 4 API-powered agents complete a full linear game flow (INIT → SPEAKING → VOTING → REACTION → END) without crashes or JSON parsing errors.
- Structured output (inner_thought + public_statement) is consistently enforced across all LLM providers.
- Post-game JSON log is correctly generated with full episode data.

---

## 3. Core Design Decisions (Locked)

These decisions are finalized and must be treated as hard constraints in all downstream documents.

| # | Decision | Detail |
|---|---|---|
| D1 | **Fixed Agent Count** | Always exactly **4 agents**: 1 Imposter + 3 Villagers. Not configurable. |
| D2 | **Agent Types** | Agents can be `AI` or `Human`. Architecture must support both from day one. By default, all 4 are AI. |
| D3 | **Memory Scope** | **Full episode history.** Agents receive all Speaking and Deliberation messages from all rounds in their prompt context. `inner_thought` is never shared cross-agent. Elimination = agent is permanently silent. |
| D4 | **LLM Providers** | **API-only.** Supported: Groq, Gemini (Google GenAI), OpenAI, DeepSeek. No local/Ollama models. |
| D5 | **Provider Config** | Configurable in the pre-game UI. Can be uniform (all agents same provider) or per-agent (each uses a different provider). **Cannot be changed mid-game.** |
| D6 | **Human Role Assignment** | Human player role (Imposter or Villager) is **random by default** (same fairness as AI agents). Optionally configurable in pre-game UI. |
| D7 | **Deliberation Format** | Dynamic **priority-based router** — rebuttal → zero-turn → one-turn → random order, budget-capped at `alive_count × 4` messages, with ping-pong cooldown guard. |
| D8 | **Elimination Rule** | Being voted out = **immediately and permanently eliminated**. No last-word guessing mechanic. |
| D9 | **Post-Elimination Reaction** | After elimination, **all surviving agents are informed of the result** (who was eliminated and what their role was) and must generate a **reaction statement** (public) + inner_thought. This creates dramatic moments — e.g., an agent who voted confidently realizing they eliminated the wrong person. |

---

## 4. Product Architecture

| Layer | Technology | Notes |
|---|---|---|
| Core Language | Python 3.11+ | |
| State Orchestration | `langgraph` | StateGraph with 7 nodes + 2 conditional routers |
| LLM Integration | `langchain` provider-agnostic wrappers | Groq, Google GenAI, OpenAI, DeepSeek |
| Data Validation | `pydantic` v2 | Frozen models, `model_validator`, `include_raw=True` |
| Frontend | Next.js 16 (App Router) + Tailwind CSS 4 | Zustand stores, Framer Motion animations |
| Real-time | WebSocket + Redis pub/sub | Per-episode channel, historical catch-up via Redis list |
| Persistence | PostgreSQL 16 + SQLAlchemy async | `EpisodeExport` stored via repository pattern |
| Infrastructure | Docker Compose | 4 services: postgres, redis, api, web |

---

## 5. Game Loop State Machine

The episode follows a directed graph. Each node is a LangGraph node.

```
[INIT]
  │
  ▼
[SPEAKING_PHASE]  ←──────────────────────────────────┐
  │                                                   │
  ▼                                                   │
[DELIBERATION_PHASE]                                  │
  │  (time-boxed, sequential round-robin)             │
  ▼                                                   │
[POLLING_PHASE]                                       │
  │                                                   │
  ├─ VOTE_NOW > 50% ──► [VOTING_PHASE]                │
  │                          │                        │
  │                          ▼                        │
  │                   [REACTION_PHASE]                │
  │                          │                        │
  │                          ▼                        │
  │                     [ENDGAME?]                    │
  │                      /      \                     │
  │              Yes (winner)   No (continue)─────────┘
  │
  └─ SKIP ≥ 50% ──────────────────────────────────────┘
```

### Phase Descriptions

#### [INIT]
- System randomly assigns: 1 Imposter, 3 Villagers
- System selects a Topic (e.g., *Fruit*) and a Secret Word (e.g., *Durian*)
- Villagers receive the Secret Word; Imposter only receives the Topic
- Turn order is randomized; each agent is assigned a display color
- Pre-game config is locked: providers, models, human/AI assignments

#### [SPEAKING_PHASE]
- Each alive agent, **in turn order**, delivers exactly **one descriptive statement** about their word/topic
- Agents have access to: their role, their word (or topic), and all previous statements in this round
- Output: `inner_thought` + `public_statement`

#### [DELIBERATION_PHASE]
- **Time-boxed** (configurable duration, e.g., 60 seconds of simulated turns)
- Agents take turns in **circular sequential order** (Agent A → B → C → D → A → ...)
- Each turn: agent reads the full deliberation history of the current round and responds
- Purpose: build trust, cast suspicion, strategize
- Agents do not know when the phase will end (creates time pressure authenticity)
- Output per turn: `inner_thought` + `public_statement`

#### [POLLING_PHASE]
- Each alive agent submits a **secret binary vote**: `VOTE_NOW` or `SKIP`
- Votes are hidden until all are cast, then revealed simultaneously
- Routing:
  - `VOTE_NOW` > 50% of alive agents → proceed to `[VOTING_PHASE]`
  - `SKIP` ≥ 50% → loop back to `[SPEAKING_PHASE]` (Round N+1, fresh context)
- Output: `inner_thought` + `poll_vote` (enum: `VOTE_NOW` | `SKIP`)

#### [VOTING_PHASE]
- Each alive agent **nominates one other alive agent** for elimination
- Votes are hidden until all are cast, then revealed simultaneously
- Agent with the most votes is eliminated. **Tie-breaking: random selection among tied candidates.**
- Eliminated agent is permanently removed from the game
- Output: `inner_thought` + `vote_target` (agent ID)

#### [REACTION_PHASE]
- System announces: *"[Agent X] has been eliminated. They were the [Role]."*
- All **surviving** agents receive this announcement and must respond
- Output: `inner_thought` + `public_statement` (reaction)
- This phase creates the game's most dramatic moments and is a key data source for behavioral analysis

#### [ENDGAME]
- **Villagers win** if the eliminated agent is the Imposter
- **Imposter wins** if they survive to be the last agent standing, or if all Villagers are eliminated before the Imposter is caught
- Game ends immediately when a win condition is met
- If no winner after N rounds (configurable max rounds safety cap), declare a draw

---

## 6. Detailed Feature Requirements

### Epic 1: Agent Cognitive Design (The "Brain")

**FR1.1 — Structured Output (All Phases)**
Every LLM call must return a strict Pydantic-validated JSON object. The exact schema varies by phase:

| Phase | Required Fields |
|---|---|
| Speaking | `inner_thought`, `public_statement` |
| Deliberation | `inner_thought`, `public_statement` |
| Polling | `inner_thought`, `poll_vote` (enum) |
| Voting | `inner_thought`, `vote_target` (agent ID) |
| Reaction | `inner_thought`, `public_statement` |

**FR1.2 — Dynamic Context Injection**
Each LLM call receives a dynamically assembled prompt containing:
- Agent's role and secret word (or topic, if Imposter)
- Current phase description and rules
- Full chat history of the **current round only**
- List of currently alive agents

**FR1.3 — Agent Type Abstraction**
The system must define an `Agent` interface/base class that both `AIAgent` and `HumanAgent` implement. This enables future human-in-the-loop play without refactoring the game engine.

### Epic 2: Game Engine & Orchestration

**FR2.1 — GameState Object**
A central `GameState` must track:
- Episode ID, current round number, current phase
- All agents (ID, name, display color, type: AI/Human, provider config, role, alive status)
- Full chat history per round (keyed by round number)
- Vote history (polling and voting)
- Winner (if determined)

**FR2.2 — Pre-Game Configuration**
Before each episode, the system presents a configuration step:
- Set LLM provider and model **per agent** (or set all at once)
- Optionally designate one agent slot as `Human`
- Optionally override human player's role assignment (default: random)
- Set deliberation time limit and max rounds safety cap

**FR2.3 — Voting & Routing Logic**
- Polling vote counting with 50% threshold routing
- Voting elimination with random tie-breaking
- Dead agent removal from all future turns and vote pools

### Epic 3: Observability & Logging

**FR3.1 — Terminal Interface (rich)**
- Each agent has a unique, consistent display color throughout the episode
- `public_statement`: displayed in agent's color, bold
- `inner_thought`: displayed dim, italic, prefixed with `[💭 Agent Name]`
- Phase transitions displayed as clearly demarcated banners
- Vote reveal displayed as a formatted table

**FR3.2 — Post-Game JSON Log**
At episode end, dump a complete log to `logs/<episode_id>_<timestamp>.json` containing:
- Full `GameState` snapshot
- All LLM inputs and outputs per turn (for analysis and prompt optimization)
- Episode metadata: providers used per agent, total token usage (if available), winner, duration

---

## 7. Roadmap & Phasing

### Sprint 1 — Core MVP (Linear Pipeline) ✅
- [x] Scaffold project structure and dependency setup
- [x] Implement all Pydantic schemas for LLM outputs and GameState
- [x] Implement `AIAgent` with multi-provider support (Groq, Gemini, OpenAI, DeepSeek)
- [x] Build linear pipeline: `INIT → SPEAKING → VOTING → REACTION → ENDGAME`
- [x] ~~Implement `rich` terminal rendering~~ — superseded by Next.js web frontend
- [x] Implement JSON log exporter → persisted `EpisodeExport` via PostgreSQL

### Sprint 2 — Full State Machine ✅
- [x] Integrate LangGraph cyclical loop with dynamic conditional routing
- [x] Implement `DELIBERATION_PHASE` with **dynamic priority-based router** (budget-based, intent-aware, ping-pong guard)
- [x] Implement `POLLING_PHASE` with threshold-based routing
- [x] Implement pre-game configuration UI → **Next.js 16 web UI** (3-step wizard with live API key monitor)
- [x] WebSocket streaming via Redis pub/sub — real-time game feed
- [x] Model tiering (smart model for reasoning phases, fast model for polling/reaction)
- [x] API key isolation (4 isolated Groq keys round-robin per agent)
- [x] Quota tracking with provider exhaustion detection

### Sprint 2 Scope Creep (Over-Delivery)
The following were delivered alongside Sprint 2 but were not in the original scope:
- Dockerized monorepo (Postgres 16 + Redis 7 + FastAPI + Next.js)
- Structured output via LangChain `.with_structured_output(include_raw=True)`
- Retry logic: 1 semantic retry, 3 network retries, rate-limit passthrough, Groq fallback
- Zustand state management for setup wizard + WebSocket-driven game store
- Frontend animations (Framer Motion typing indicators, animated chat feed)

### Sprint 3 — Human Player & Evaluation ⬜
- [ ] Implement `HumanAgent` interface
- [ ] Implement asymmetric provider matchups and comparison tooling
- [ ] Develop log analysis scripts: Imposter win rate, vote accuracy, deception quality metrics

---

## 8. Out of Scope (For Now)

- ~~Web UI (React/Vue)~~ — now delivered: Next.js 16 App Router with
  Tailwind CSS 4, Framer Motion animations, Zustand stores, Redis-pub/sub
  WebSocket streaming to the game feed
- Local/Ollama models — API-only by design decision
- ~~Cross-round persistent memory~~ — now delivered: agents receive the
  full episode history in their prompt (all rounds). `inner_thought` is
  still private per phase call — never shared cross-agent.
- Model fine-tuning (RLHF/PPO) — out of scope for simulation phase
- Networked multiplayer (LAN/Internet)
