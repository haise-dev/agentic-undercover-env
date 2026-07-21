# 🗂️ Data Schema Specification

**Document:** `DATA_SCHEMA.md`
**Project:** Agentic Undercover Environment (AUE)
**Version:** 1.0.0
**Status:** LOCKED — Derived from PRD v1.1.0 and GAME_RULES_SPEC v1.0.0
**Language:** English (implementation reference)

> This document is the **single source of truth** for all data structures in AUE. Every Pydantic model, enum, and type alias used across the engine, agents, and logging system is defined here. No model may be invented ad-hoc in implementation; all additions must be reflected here first.

---

## 1. Design Principles

- **Immutability by default:** All models use `model_config = ConfigDict(frozen=True)` unless explicitly stated as mutable. Mutable models (like `GameState`) are marked with `frozen=False` and must only be mutated by the game engine, never by agent code.
- **Strict validation:** All models use Pydantic v2 with `model_config = ConfigDict(strict=True)` where appropriate. No coercion between incompatible types.
- **Separation of private and public data:** `inner_thought` fields are never included in any object passed to another agent's context. Public broadcast objects strip private fields before transmission.
- **JSON-serializable:** All models must be fully serializable via `model.model_dump()` for log export. No non-serializable field types (e.g., raw LangChain objects) are stored in schema models.

---

## 2. Enumerations

All enums are `str` enums for JSON serialization compatibility.

```python
from enum import Enum

class Role(str, Enum):
    VILLAGER = "villager"
    IMPOSTER = "imposter"

class AgentType(str, Enum):
    AI     = "ai"
    HUMAN  = "human"

class Phase(str, Enum):
    INIT          = "init"
    SPEAKING      = "speaking"
    DELIBERATION  = "deliberation"
    POLLING       = "polling"
    VOTING        = "voting"
    REACTION      = "reaction"
    ENDGAME       = "endgame"

class PollVote(str, Enum):
    VOTE_NOW = "vote_now"
    SKIP     = "skip"

class GameResult(str, Enum):
    VILLAGERS_WIN = "villagers_win"
    IMPOSTER_WINS = "imposter_wins"

class LLMProvider(str, Enum):
    OPENAI   = "openai"
    GEMINI   = "gemini"
    GROQ     = "groq"
    DEEPSEEK = "deepseek"

class DeliberationIntent(str, Enum):
    """Semantically-typed intent emitted by an agent on each deliberation turn.

    The router inside the LangGraph graph inspects this field to decide the
    next speaker (e.g. ACCUSE / QUESTION / AGREE_WITH require a target_name).
    """
    GENERAL_OPINION = "general_opinion"
    ACCUSE          = "accuse"
    QUESTION        = "question"
    DEFEND          = "defend"
    AGREE_WITH      = "agree_with"
    SUGGEST_VOTE    = "suggest_vote"
    SUGGEST_SKIP    = "suggest_skip"
```

---

## 3. Configuration Models

These models are populated **before** the episode starts and frozen for the duration of the game.

### 3.1 `AgentLLMConfig`

Configuration for a single AI agent's LLM backend. Frozen after INIT.

```python
class AgentLLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: LLMProvider
    # Heavy-reasoning model used for SPEAKING, DELIBERATION, VOTING.
    # e.g., "llama-3.3-70b-versatile", "gpt-4o", "gemini-2.0-flash".
    smart_model_name: str
    # Cheap/fast model used for POLLING and REACTION only.
    # Separately configurable so quota cost can be optimized.
    fast_model_name: str
    temperature: float = 0.8
    max_tokens: int | None = None  # None = provider default

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_model_name(cls, data: Any) -> Any:
        """Backward compat: legacy payloads used a single `model_name`.
        Promotes it to *both* slots so old configs keep working."""
        if isinstance(data, dict) and "model_name" in data:
            data.setdefault("smart_model_name", data["model_name"])
            data.setdefault("fast_model_name", data["model_name"])
        return data
```

**Model-tiering rationale:** REACTION and POLLING phases use the lightweight
`fast_model_name`; all other phases use `smart_model_name`. This roughly halves
the total token spend while preserving reasoning quality where it matters.

### 3.2 `AgentConfig`

Static configuration for one agent slot. Frozen after INIT.

```python
class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Unique identifier. Format: "agent_{index}" e.g., "agent_0", "agent_1"
    agent_id: str
    # Display name shown in the UI and event stream. e.g., "Alice"
    display_name: str
    # Hex/CSS color used in the chat feed. Set client-side during setup.
    display_color: str
    agent_type: AgentType
    # Only required when agent_type == AgentType.AI
    llm_config: AgentLLMConfig | None = None
    # Rotates 1..4 across the 4 agents so that GROQ rate-limits are
    # spread across 4 isolated API keys. 1-based, validated ge=1, le=4.
    api_key_index: int = Field(default=1, ge=1, le=4)
```

### 3.3 `EpisodeConfig`

Top-level pre-game configuration. Frozen after INIT. Captured in the log.

```python
class EpisodeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Unique episode identifier. Format: UUID4 string.
    episode_id: str
    topic: str           # e.g., "Fruit"
    secret_word: str     # e.g., "Durian" — never exposed to Imposter during play
    # Ordered list of 4 agents. Index = display order, not turn order.
    agents: list[AgentConfig]  # len == 4, enforced by validator
    # Max Speaking rounds before a forced vote.
    max_rounds: int = 3

    @field_validator("agents")
    @classmethod
    def must_have_four_agents(cls, v: list) -> list:
        if len(v) != 4:
            raise ValueError("Episode must have exactly 4 agents.")
        return v
```

---

## 4. Role Assignment Model

Generated during INIT. Contains each agent's role and their word (or lack thereof). This object is **never transmitted as a whole** — each agent receives only their own slice.

```python
class AgentRoleAssignment(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    role: Role
    # Villagers receive the Secret Word. Imposter receives None.
    secret_word: str | None
    topic: str
```

---

## 5. Agent Output Models (Per Phase)

These are the structured outputs returned by every LLM call. All are validated by Pydantic before being consumed by the game engine. `inner_thought` is **always present** and **always private**.

### 5.1 `SpeakingOutput`

Returned during the **Speaking Phase**.

```python
class SpeakingOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Private reasoning. Never shown to other agents. Logged to JSON only.
    inner_thought: str
    # The single descriptive sentence broadcast to all agents.
    # Must not directly state the secret_word (prompt-enforced, not validated here).
    public_statement: str
```

### 5.2 `DeliberationOutput`

Returned on each **Deliberation Phase** turn. The schema is a 3-step CoT
chain (`step_1_audit` → `step_2_anti_repetition` → `step_3_intent_and_target`)
plus an explicit semantically-typed `intent` (and conditional `target_name`).

```python
class DeliberationOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    # CoT step 1 — audit the current situation (what's been said, who is sus)
    step_1_audit: str
    # CoT step 2 — anti-repetition check against recent messages
    step_2_anti_repetition: str
    # CoT step 3 — decide on this turn's intent & (if applicable) target
    step_3_intent_and_target: str
    # The single broadcast sentence
    public_statement: str
    intent: DeliberationIntent
    target_name: str | None = None  # required for ACCUSE / QUESTION / AGREE_WITH

    @property
    def inner_thought(self) -> str:
        """Virtual field used by code that wants a single `inner_thought`
        string. Concatenates the 3 CoT steps into the legacy layout:
            Audit: {...}
            Anti-Repetition: {...}
            Intent: {...}
        """
        return (
            f"Audit: {self.step_1_audit}\n"
            f"Anti-Repetition: {self.step_2_anti_repetition}\n"
            f"Intent: {self.step_3_intent_and_target}"
        )

    @model_validator(mode="after")
    def _target_required_for_directional_intents(self) -> "DeliberationOutput":
        requires_target = {
            DeliberationIntent.ACCUSE,
            DeliberationIntent.QUESTION,
            DeliberationIntent.AGREE_WITH,
        }
        if self.intent in requires_target and not self.target_name:
            raise ValueError(
                f"intent='{self.intent}' requires a non-empty target_name"
            )
        return self
```

**Intent ↔ target_name rules:**
- `target_name` is the displayed name (e.g. `"Alice"`), not `agent_id`.
- The router resolves `target_name` → `agent_id` for rebuttal priority.
- `intent == ACCUSE | QUESTION | AGREE_WITH` requires `target_name` to be set.
- Other intents (`GENERAL_OPINION`, `DEFEND`, `SUGGEST_VOTE`, `SUGGEST_SKIP`)
  allow `target_name = None`.
- Pydantic-normalized enum values are lowercase strings (see §2).

### 5.3 `PollingOutput`

Returned during the **Polling Phase**.

```python
class PollingOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    inner_thought: str
    poll_vote: PollVote  # "vote_now" | "skip"
```

### 5.4 `VotingOutput`

Returned during the **Voting Phase**.

```python
class VotingOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    inner_thought: str
    # Must be a valid agent_id of a currently alive agent (not self).
    # Engine validates; re-prompts once on invalid; random fallback on second failure.
    vote_target: str
```

### 5.5 `ReactionOutput`

Returned during the **Reaction Phase** by both the eliminated agent (last words) and surviving agents.

```python
class ReactionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    inner_thought: str
    public_statement: str
```

---

## 6. Chat & Event Message Models

These models form the **public chat history** injected into each agent's context. They contain only public-facing data — no `inner_thought` is ever included.

### 6.1 `PublicMessage`

A single broadcast message visible to all agents.

```python
class PublicMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    display_name: str
    phase: Phase
    # Speaking round index (1, 2, or 3). Used for episode-wide history.
    round_number: int
    # Deliberation segment index (since segments are now dynamic, this can
    # exceed 2). None for non-deliberation phases.
    deliberation_round: int | None = None
    content: str
    timestamp: str  # ISO 8601 UTC
    # Mirrors of the deliberation output for routing downstream events.
    # Populated only when phase == DELIBERATION.
    intent: DeliberationIntent | None = None
    target_name: str | None = None
```

### 6.2 `SystemAnnouncement`

A system-level message broadcast to all agents. Used for role reveals, tie-break notices, forced vote notices, etc.

```python
class SystemAnnouncement(BaseModel):
    model_config = ConfigDict(frozen=True)

    phase: Phase
    round_number: int
    # Human-readable announcement text injected into agent context.
    # e.g., "Agent Bob has been eliminated. Their role was: Villager."
    content: str
    timestamp: str  # ISO 8601 UTC string
```

### 6.3 `RoundContext`

The full context slice passed to an agent for a given turn. Assembled by the
engine on-demand from `GameState`; never stored back into `GameState`.

```python
class RoundContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    role_assignment: AgentRoleAssignment          # Private to this agent
    current_phase: Phase
    current_round: int
    deliberation_round: int | None
    # All public messages from the current Speaking round AND the current
    # Deliberation segment (deliberation messages are split out in
    # prompt_builder for separate formatting).
    public_history: list[PublicMessage]
    announcements: list[SystemAnnouncement]
    # [{agent_id, display_name}] of currently alive agents
    alive_agents: list[dict[str, str]]
    # Comma-separated name list used in system prompts
    all_agent_names: str
    game_language: str
    # True if this Speaking round is the final one — poll will force a vote
    is_final_round: bool = False
```

---

## 7. Vote Record Models

### 7.1 `PollRecord`

A record of one agent's poll vote. Stored in GameState after the Polling Phase.

```python
class PollRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    poll_vote: PollVote
    inner_thought: str   # Stored in log only
    round_number: int
```

### 7.2 `VoteRecord`

A record of one agent's elimination vote. Stored in GameState after the Voting Phase.

```python
class VoteRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    voter_agent_id: str
    target_agent_id: str
    inner_thought: str   # Stored in log only
```

### 7.3 `EliminationResult`

The resolved outcome of the Voting Phase.

```python
class EliminationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    eliminated_agent_id: str
    # Raw vote tally: {agent_id: vote_count}
    vote_tally: dict[str, int]
    # True if elimination was resolved by random tie-break
    was_tiebreak: bool
    # If tiebreak, lists all agent_ids that were tied
    tiebreak_candidates: list[str] | None = None
```

---

## 8. Central Game State

`GameState` is the **single mutable object** owned and mutated exclusively
by the game engine. It tracks the complete live state of an episode and the
dynamic deliberation-segment bookkeeping used by the router.

```python
class GameState(BaseModel):
    model_config = ConfigDict(frozen=False)  # Mutable — engine only

    # ── Identity ──────────────────────────────────────────────────
    episode_id: str
    config: EpisodeConfig

    # ── Role Assignments ──────────────────────────────────────────
    # Keyed by agent_id. Engine reads; never passed wholesale to agents.
    role_assignments: dict[str, AgentRoleAssignment]

    # ── Turn Order ────────────────────────────────────────────────
    # Current Speaking-phase turn order (re-randomized per Speaking round)
    current_turn_order: list[str]

    # ── Progress Tracking ─────────────────────────────────────────
    current_phase: Phase = Phase.INIT
    current_round: int = 1                       # Speaking round index
    current_deliberation_round: int = 1          # Index within a segment

    # ── Agent Status ──────────────────────────────────────────────
    # agent_id → alive (True/False). All start True.
    agent_alive: dict[str, bool]

    # ── Chat History (full episode — never reset) ─────────────────
    all_messages: list[PublicMessage]
    all_announcements: list[SystemAnnouncement]

    # ── Vote History ──────────────────────────────────────────────
    # Polling votes per round: {round_number: [PollRecord, ...]}
    poll_history: dict[int, list[PollRecord]] = {}
    # Voting-phase records (exactly one voting per episode)
    vote_records: list[VoteRecord] = []
    elimination_result: EliminationResult | None = None

    # ── Endgame ───────────────────────────────────────────────────
    result: GameResult | None = None
    winning_agent_ids: list[str] | None = None

    # ── Timestamps ────────────────────────────────────────────────
    started_at: str                              # ISO 8601 UTC
    ended_at: str | None = None

    # ── Deliberation tracking (dynamic-router bookkeeping) ────────
    next_speaker_id: str | None = None
    deliberation_message_count: int = 0          # ≥ budget ⇒ end segment
    turns_count: dict[str, int]                  # agent_id → # turns in segment
    speakers_this_round: set[str]                # agent_ids that have spoken

    def reset_deliberation_tracking(self) -> None:
        """Reset all deliberation-segment bookkeeping fields.
        Called at the start of every new deliberation segment."""
        self.next_speaker_id = None
        self.deliberation_message_count = 0
        self.turns_count = {}
        self.speakers_this_round = set()
        self.current_deliberation_round = 1

    # ── Derived helpers (computed on access) ──────────────────────

    @property
    def alive_agent_ids(self) -> list[str]:
        """Stable ordering of agent_ids still alive."""
        return [aid for aid, alive in self.agent_alive.items() if alive]

    @property
    def imposter_id(self) -> str:
        """Single Imposter's agent_id. Raises StopIteration if not yet set."""
        return next(
            aid for aid, ra in self.role_assignments.items()
            if ra.role == Role.IMPOSTER
        )

    @property
    def messages_in_current_round(self) -> list[PublicMessage]:
        """Messages from the current Speaking round only.
        Used by `messages_in_current_round` for context injection."""
        return [m for m in self.all_messages if m.round_number == self.current_round]
```

**Note on deliberation dynamics:** the router (see `ARCHITECTURE.md` §3) caps
each deliberation segment at `alive_count × 4` messages and rotates speaker
priority among `direct rebuttal → zero-turn agents → one-turn agents →
free-for-all`. The fields in the *Deliberation tracking* block above are the
ones the router reads and writes — they are reset on every new segment.

---

## 9. Full Action Log Model

Each discrete agent action (one LLM call) is recorded as an `ActionLog` entry. These are accumulated throughout the episode and written to the JSON export file at Endgame.

```python
class ActionLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    episode_id: str
    agent_id: str
    phase: Phase
    round_number: int
    deliberation_round: int | None = None

    # The full context passed to the LLM (RoundContext serialized to dict)
    prompt_context: dict

    # The raw LLM response before Pydantic validation
    raw_llm_response: str

    # The validated structured output (one of the Output models, serialized to dict)
    structured_output: dict

    # Token usage if available from the provider response
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    timestamp: str  # ISO 8601 UTC
    # Wall-clock latency of the LLM call in milliseconds
    latency_ms: int | None = None
```

---

## 10. Episode Export (Persisted Log)

At Endgame, the engine builds the complete episode payload and persists it
via `EpisodeRepository.create()` to PostgreSQL (see `src/engine/nodes/endgame_node.py`).

**File path:** persisted to PostgreSQL via `EpisodeRepository.create()` — see `EpisodeRunner.run()` in `src/engine/runner.py`. The JSON dump itself is no longer on disk; consumers fetch the export through the repository.

```python
class EpisodeExport(BaseModel):
    model_config = ConfigDict(frozen=True)

    # ── Episode Identity ───────────────────────────────────────────
    episode_id: str
    started_at: str
    ended_at: str
    duration_seconds: float

    # ── Configuration ─────────────────────────────────────────────
    config: EpisodeConfig   # topic, secret_word, agent configs

    # ── Role Assignments ──────────────────────────────────────────
    # Full role assignments revealed post-game (includes Imposter's identity)
    role_assignments: list[AgentRoleAssignment]

    # ── Result ────────────────────────────────────────────────────
    result: GameResult
    winning_agent_ids: list[str]
    elimination_result: EliminationResult

    # ── Full History ──────────────────────────────────────────────
    all_messages: list[PublicMessage]
    all_announcements: list[SystemAnnouncement]
    poll_history: dict[str, list[PollRecord]]  # round_number (str key for JSON) → records
    vote_records: list[VoteRecord]

    # ── Full Action Log ───────────────────────────────────────────
    # Ordered list of every LLM call made during the episode
    action_logs: list[ActionLog]

    # ── Aggregate Stats ───────────────────────────────────────────
    total_rounds_played: int
    total_llm_calls: int
    total_tokens_used: int | None   # None if any provider didn't return usage
    # Per-agent token breakdown: {agent_id: total_tokens}
    tokens_per_agent: dict[str, int | None]
```

---

## 11. Model Dependency Graph

```
EpisodeConfig
  └── AgentConfig (×4)
        └── AgentLLMConfig (if AI)

GameState
  ├── EpisodeConfig
  ├── AgentRoleAssignment (×4, keyed by agent_id)
  ├── PublicMessage (list, appended each turn)
  ├── SystemAnnouncement (list, appended on key events)
  ├── PollRecord (nested in poll_history dict)
  ├── VoteRecord (list)
  └── EliminationResult (set after Voting Phase)

RoundContext (ephemeral, built per LLM call, not stored in GameState)
  ├── AgentRoleAssignment (single agent's slice)
  └── PublicMessage (filtered to current round)

ActionLog (one per LLM call)
  ├── RoundContext (serialized as prompt_context)
  └── Structured Output (one of: Speaking/Deliberation/Polling/Voting/ReactionOutput)

EpisodeExport (final JSON dump)
  ├── EpisodeConfig
  ├── GameState fields (flattened)
  └── ActionLog (list, full episode)
```

---

## 12. Field Visibility Matrix

This table defines which fields are visible to whom. Critical for prompt assembly.

| Field | Agent (own) | Agent (others) | Engine | Logger |
|---|:---:|:---:|:---:|:---:|
| `role` | ✅ | ❌ | ✅ | ✅ |
| `secret_word` (Villager) | ✅ | ❌ | ✅ | ✅ |
| `secret_word` (Imposter) | ❌ | ❌ | ✅ | ✅ |
| `topic` | ✅ | ✅ (via own prompt) | ✅ | ✅ |
| `inner_thought` | ✅ (own only) | ❌ | ✅ | ✅ |
| `public_statement` | ✅ | ✅ | ✅ | ✅ |
| `poll_vote` | ✅ (own only, before reveal) | ✅ (after reveal) | ✅ | ✅ |
| `vote_target` | ✅ (own only, before reveal) | ✅ (after reveal) | ✅ | ✅ |
| `elimination_result` | ✅ (via announcement) | ✅ (via announcement) | ✅ | ✅ |
| `role` of eliminated agent | ✅ (via Step 2 announcement) | ✅ | ✅ | ✅ |
| Other agents' `role` | ❌ (until elimination) | ❌ | ✅ | ✅ |

---

## 13. Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Agent IDs | `agent_{0..3}` | `"agent_0"` |
| Display names | Configurable string | `"Alice"`, `"Bob"` |
| Episode IDs | UUID4 | `"f47ac10b-58cc-..."` |
| Timestamps | ISO 8601 UTC | `"2026-06-29T10:00:00Z"` |
| Log filenames | `{episode_id}_{YYYYMMDD_HHMMSS}.json` | `"f47ac10b_20260629_100000.json"` |
| Pydantic models | `PascalCase` | `GameState`, `VotingOutput` |
| Enum values | `UPPER_SNAKE_CASE` | `PollVote.VOTE_NOW` |
| Python files (future) | `snake_case.py` | `game_state.py`, `agent_output.py` |
