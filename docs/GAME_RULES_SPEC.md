# 📜 Game Rules Specification

**Document:** `GAME_RULES_SPEC.md`
**Project:** Agentic Undercover Environment (AUE)
**Version:** 1.0.0
**Status:** LOCKED — Derived from design Q&A sessions (2026-06-29)
**Language:** English (implementation reference)

> This document is the single source of truth for all game mechanics, win conditions, edge cases, and phase-level rules. All engine code, prompt templates, and test cases must conform to this specification.

---

## 1. Overview

AUE simulates a 4-player social deduction game inspired by *Undercover (谁是卧底)*. Each episode is a one-shot match: there is **exactly one elimination event**, and the game ends immediately after. The entire gameplay arc builds toward a single, high-stakes voting decision.

**Core tension:**
- Villagers must identify the Imposter without revealing the Secret Word.
- The Imposter must blend in using only a Topic, with no knowledge of the exact Secret Word.
- The Polling mechanism creates strategic pressure: voting too early risks a wrong elimination; waiting too long risks giving the Imposter more clues to work with.

---

## 2. Roles & Information Asymmetry

### 2.1 Fixed Composition (Non-Configurable)

| Role | Count | Receives |
|---|---|---|
| **Villager** | 3 | Topic + Secret Word |
| **Imposter** | 1 | Topic only (no Secret Word) |

> **Design rationale:** Knowing only the Topic forces the Imposter to use strategically safe, ambiguous language. A smart Imposter exploits the overlap between the Topic and any plausible word within it. A smart Villager must be specific enough to signal teammates but not so specific that they hand the Imposter a free deduction.

### 2.2 Agent Types

Each of the 4 slots can be filled by either an `AIAgent` or a `HumanAgent`. The game engine treats both identically at the mechanic level. Default: all 4 slots are `AIAgent`.

### 2.3 What Each Role Knows (Per Round)

| Information | Villager | Imposter |
|---|---|---|
| Own role | ✅ | ✅ |
| Topic | ✅ | ✅ |
| Secret Word | ✅ | ❌ |
| Other agents' roles | ❌ | ❌ |
| Public chat history (current round) | ✅ | ✅ |
| Inner thoughts of other agents | ❌ | ❌ |

> **Memory scope:** Agents receive the **full episode history** in their prompt
(all Speaking statements + all Deliberation messages across all rounds).
The vignette of *"chat history resets on SKIP"* was a design-time heuristic;
the engine now feeds the full history so agents can make evidence-based decisions.
Each agent's `inner_thought` is **never visible** to other agents.
Elimination is permanent and silent — a dead agent generates no further output.

---

## 3. Episode Setup (INIT Phase)

Before the first Speaking round, the system performs the following steps **once per episode**:

1. **Word assignment:** System selects one Topic (e.g., *Fruit*) and one Secret Word within that topic (e.g., *Durian*). The Secret Word must not be the Topic itself.
2. **Role assignment:** One agent slot is randomly designated Imposter; the remaining three are Villagers.
3. **Information delivery:** Each agent receives a private system prompt with their role and word information. This is never shared with other agents.
4. **Turn order generation:** A random permutation of the 4 agents is generated. This is the **initial turn order** used in Speaking Round 1.
5. **Display assignment:** Each agent is assigned a unique display color (used throughout the episode for terminal rendering).
6. **Provider lock:** LLM provider and model configuration per agent is frozen. No changes allowed after INIT.

---

## 4. Phase-by-Phase Rules

### 4.1 Speaking Phase

**Trigger:** Start of each game round (Round 1, 2, 3).
**Turn order:** Randomized at the start of each round (a new random permutation is drawn).

**Rules:**
- Each alive agent, in the randomized turn order, delivers **exactly one descriptive statement** about their word (Villagers) or their interpretation of the topic (Imposter).
- The statement must be **one sentence**. Length is not strictly capped but must be a single coherent sentence.
- **Forbidden:** Agents must not state the Secret Word directly (enforced via prompt instruction; not mechanically validated in MVP).
- Each agent has access to: their private role/word context, and all public statements made **so far in the current Speaking phase** (i.e., agents who speak later in the turn order have more information).
- Each agent produces: `inner_thought` (private) + `public_statement` (broadcast).

**Phase ends:** When all alive agents have spoken once.

---

### 4.2 Deliberation Phase

**Trigger:** Immediately after Speaking Phase ends.
**Structure:** **Dynamic budget-based segments** instead of fixed 2 equal rounds.
Each Deliberation segment runs until the budget (`alive_count × 4` messages)
is exhausted, at which point the Polling Phase triggers.

**Turn order determined by a priority-based dynamic router (§4.2.1)** instead
of a static round-robin permutation. The same router imposes a **ping-pong
cooldown guard**: after 3 consecutive ACCUSE/QUESTION messages bouncing
between the same two agents, the system forces the speaker to a different agent.

**Rules:**
- Every deliberation turn, the router selects ONE alive agent (via `next_speaker_id`)
  and the `deliberation_node` runs that agent's LLM call.
- An agent's colored bubble appears only once per deliberation segment
  (`speakers_this_round` set).
- `turns_count` guarantees every agent ≥ 2 turns before the router switches
  to free-for-all mode (*must-speak reservation*).
- Each agent produces per turn: `step_1_audit`, `step_2_anti_repetition`,
  `step_3_intent_and_target`, `public_statement`, `intent` (→ §4.2.2 INTENT SYSTEM),
  and optionally a `target_name`.
- The segment ends when `deliberation_message_count ≥ alive_count × 4`;
  the router then returns `"polling"`.

> **Strategic note (injected into agent prompts):** Agents are told that extended
> rounds give the Imposter more information. They are guided to select an intent
> on each turn (ACCUSE, DEFEND, QUESTION, etc.) and, when the intent is directional,
> to name a target.

#### 4.2.1 Dynamic Router Priorities

| Priority | Who | Condition |
|----------|-----|-----------|
| 1 | Direct rebuttal | Last message was ACCUSE/QUESTION, target is alive, NOT in must-speak mode, NOT a ping-pong loop |
| 2 | Zero-turn agents | Agents who have not spoken yet this segment |
| 3 | One-turn agents | Agents who have spoken exactly 1 time |
| 4 | Free-for-all | All agents have ≥ 2 turns, budget not exhausted → random |

**Must-speak mode:** activates when remaining budget ≤ turns needed to give
each agent at least 2 turns — skips rebuttal priority entirely.

#### 4.2.2 Intent System

Each deliberation turn carries a DeliberationIntent enum value:

| Intent | Requires target_name? | Purpose |
|--------|-----------------------|---------|
| `GENERAL_OPINION` | No | passive commentary |
| `ACCUSE` | Yes | target an agent |
| `QUESTION` | Yes | interrogate a specific agent |
| `DEFEND` | No | defend oneself |
| `AGREE_WITH` | Yes | align with another agent's opinion |
| `SUGGEST_VOTE` | No | push toward voting |
| `SUGGEST_SKIP` | No | push toward skipping |

The router **consumes** intent + target_name to select the next speaker.
The frontend **renders** intent badge colors on each message bubble.

---

### 4.3 Polling Phase

**Trigger:** Immediately after Deliberation Phase ends.
**Purpose:** Agents decide collectively whether to proceed to a binding vote or continue deliberating.

**Rules:**
- Each alive agent simultaneously (no turn order, parallel) submits a **binary secret vote**: `VOTE_NOW` or `SKIP`.
- Votes are hidden until all are cast, then revealed simultaneously.
- Each agent produces: `inner_thought` + `poll_vote` (enum: `VOTE_NOW` | `SKIP`).

**Routing logic:**

| Condition | Outcome |
|---|---|
| ≥ 2 agents vote `VOTE_NOW` (≥ 50%) | → Proceed to **Voting Phase** |
| ≤ 1 agent votes `VOTE_NOW` (< 50%) | → Return to **Speaking Phase** (Round N+1) |
| This is **Round 3** (max cap reached) | → **Force proceed** to Voting Phase, regardless of poll result |

> **Max round cap:** The game runs for a maximum of **3 Speaking rounds**. If the Polling Phase of Round 3 is reached, all agents are forced to proceed to Voting Phase. This is communicated to agents in the Round 3 prompt to reflect the urgency.

---

### 4.4 Voting Phase

**Trigger:** Polling Phase routes `VOTE_NOW`, or Round 3 max cap is triggered.
**Purpose:** Binding elimination vote. This is the only elimination event in the episode.

**Rules:**
- Each alive agent simultaneously submits a **nomination**: the Agent ID of one other alive agent they wish to eliminate.
- Agents **cannot vote for themselves**.
- Votes are hidden until all are cast, then revealed simultaneously.
- Each agent produces: `inner_thought` + `vote_target` (Agent ID).

**Elimination resolution:**
- The agent with the **most votes** is eliminated.
- **Tie-breaking:** If two or more agents share the highest vote count, one is selected **uniformly at random** from the tied candidates. The system announces the tie and the tie-break result.

**Phase ends:** One agent is designated as eliminated. They are permanently removed from all future phases (if any).

---

### 4.5 Reaction Phase

**Trigger:** Immediately after the eliminated agent is identified (but before their role is publicly revealed).
**Purpose:** Dramatic denouement. Creates the most behaviorally rich data in the episode.

**Sequence (strictly ordered):**

#### Step 1 — Eliminated Agent: Last Words
- The eliminated agent is informed that they have been voted out.
- They deliver a **final public statement** ("last words") — a defense, accusation, or farewell.
- They do **not yet know** whether survivors know their role; the role reveal has not happened yet.
- Output: `inner_thought` + `public_statement` (last words).

#### Step 2 — Role Reveal (System Announcement)
- System broadcasts to all agents: *"[Agent Name] has been eliminated. Their role was: [Role]."*
- This is the moment of truth — survivors now know if they voted correctly.

#### Step 3 — Survivor Reactions
- All 3 surviving agents, in a **freshly randomized order**, each deliver one reaction statement.
- Each survivor has access to: the eliminated agent's last words + the role reveal announcement.
- Survivors can express shock, satisfaction, regret, vindication — anything contextually appropriate.
- Output per survivor: `inner_thought` + `public_statement` (reaction).

**Phase ends:** All 3 survivors have reacted. Proceed immediately to Endgame.

---

### 4.6 Endgame

**Trigger:** Immediately after Reaction Phase.

**Win conditions:**

| Eliminated Agent's Role | Winner |
|---|---|
| **Imposter** | 🏆 Villagers win |
| **Villager** | 🏆 Imposter wins |

**Result announcement:** System broadcasts the winner, the Secret Word (revealed for the first time to all, including the Imposter), and a summary of voting results.

**Episode ends.** No further agent output is generated after Endgame.

---

## 5. Turn Order Summary

| Phase | Order |
|---|---|
| Speaking | Random permutation, **re-drawn each Speaking round** |
| Deliberation (per segment) | **Dynamic priority router** — rebuttal → zero-turn → one-turn → random |
| Polling | Parallel (simultaneous) — no turn order |
| Voting | Parallel (simultaneous) — no turn order |
| Reaction — Last Words | Eliminated agent only (fixed: always first) |
| Reaction — Survivors | Random permutation of 3 surviving agents |

---

## 6. Agent Output Schema (Per Phase)

All LLM outputs must conform to a strict Pydantic schema. The `inner_thought` field is present in every phase output and is **never broadcast** to other agents.

| Phase | Output Fields |
|---|---|
| Speaking | `inner_thought`, `public_statement` |
| Deliberation | `step_1_audit`, `step_2_anti_repetition`, `step_3_intent_and_target`, `public_statement`, `intent` (DeliberationIntent enum), `target_name` (nullable, required for ACCUSE/QUESTION/AGREE_WITH) |
| Polling | `inner_thought`, `poll_vote` (`VOTE_NOW` or `SKIP`) |
| Voting | `inner_thought`, `vote_target: str` (Agent ID) |
| Reaction (Last Words) | `inner_thought`, `public_statement` |
| Reaction (Survivor) | `inner_thought`, `public_statement` |

---

## 7. Edge Cases & Rules Clarifications

### 7.1 Deliberation Pass
An agent that chooses to pass must still call the LLM and return a valid output object. The `public_statement` should be a natural-sounding pass (not a hardcoded string), and `inner_thought` should still reflect genuine reasoning. This ensures behavioral data is captured even for "quiet" turns.

### 7.2 Invalid Vote Target
If an agent submits a `vote_target` that is their own ID or an already-eliminated agent's ID, the system **re-prompts** the agent once with an error correction instruction. If the second attempt is also invalid, the system selects a random valid target on behalf of that agent and logs the incident.

### 7.3 Round 3 Force Vote
When the max round cap is triggered, agents are informed in their Round 3 Polling prompt: *"This is the final deliberation round. A vote will proceed regardless of poll results."* This prompt adjustment is intentional — it allows agents to reason about the urgency and potentially change their strategic behavior.

### 7.4 Tie in Voting
Ties are resolved by the system via `random.choice()` among tied nominees. The system announces the tie and the tie-break mechanism transparently in the terminal output before revealing the result. Agents are not re-polled.

### 7.5 Memory Reset Between Rounds
When Polling results in `SKIP` and the game returns to Speaking Phase (Round N+1):
- The **public chat history is reset** for all agents.
- A new random turn order is generated.
- Each agent's prompt will indicate: *"This is Round [N+1]. Previous rounds have concluded without a vote."*
- `inner_thought` history is never accessible to agents (only to the system logger).

### 7.6 Secret Word Revelation Timing
The Secret Word is revealed to all agents (including the Imposter) **only at Endgame**, after the Reaction Phase. It is never revealed during gameplay. This ensures that even a losing Imposter has no opportunity to retroactively use the Secret Word information during active play.

---

## 8. Complete Episode Flow (Reference)

```
┌─────────────────────────────────────────────────────────────────┐
│                          [INIT]                                 │
│  Assign roles · Select topic + word · Randomize turn order      │
│  Lock provider config · Assign display colors                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   [SPEAKING PHASE]  │  ← Random turn order (re-randomized each round)
              │  Each agent: 1 stmt │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ [DELIBERATION PHASE]│  ← Dynamic budget (alive_count × 4)
              │  Priority router    │    Router: rebuttal → 0-turn → 1-turn → random
              │  Intent + target    │    Ping-pong cooldown guard
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   [POLLING PHASE]   │  ← Simultaneous secret vote
              │  VOTE_NOW or SKIP   │
              └──────────┬──────────┘
                         │
           ┌─────────────┴──────────────┐
     ≥2 VOTE_NOW                    ≤1 VOTE_NOW
  (or max_rounds cap)            (and round < max_rounds)
           │                           │
           │                    ┌──────▼──────┐
           │                    │  Round N+1  │
           │                    │ (not reset) │
           │                    └──────┬──────┘
           │                           │
           │                    back to SPEAKING
           │
┌──────────▼──────────┐
│   [VOTING PHASE]    │  ← Simultaneous secret vote
│  Nominate a target  │    Tie → random selection
└──────────┬──────────┘
           │
┌──────────▼──────────────────────────────────────────────────────┐
│                      [REACTION PHASE]                           │
│                                                                 │
│  Step 1: Eliminated agent → Last Words (role not yet revealed)  │
│  Step 2: System announces role reveal                           │
│  Step 3: 3 survivors react (random order)                       │
└──────────┬──────────────────────────────────────────────────────┘
           │
┌──────────▼──────────┐
│     [ENDGAME]       │
│  Determine winner   │
│  Reveal Secret Word │
│  Persist export     │
└─────────────────────┘
```

---

## 9. Constraints Summary (Quick Reference for Prompt Engineering)

| Constraint | Value |
|---|---|
| Total agents | 4 (fixed) |
| Imposter count | 1 (fixed) |
| Villager count | 3 (fixed) |
| Speaking statements per agent per round | 1 sentence |
| Deliberation rounds per Speaking round | Dynamic (budget = `alive_count × 4`) |
| Max Speaking rounds before forced vote | 3 |
| Polling threshold for VOTE_NOW | ≥ 2 out of 4 agents |
| Tie-breaking mechanism | `random.choice()` among tied nominees |
| Memory scope | Full episode history (all rounds) in prompt |
| Role reveal timing | Endgame only (after Reaction Phase) |
| Eliminations per episode | Exactly 1 |
| Agent output format | Pydantic-validated JSON (all phases) |
