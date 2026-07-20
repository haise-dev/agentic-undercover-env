import random

from src.engine.graph.state import GraphState
from src.models import DeliberationIntent, Phase


def poll_router(state: GraphState) -> str:
    """
    Conditional routing logic after polling_node.
    If proceed_to_vote is True, route to voting_node.
    Otherwise, loop back to speaking_node (for the next round).
    """
    if state.get("proceed_to_vote"):
        return "voting_node"
    return "speaking_node"


def route_dynamic_deliberation(state: GraphState) -> str:
    """
    Priority-based deliberation routing logic.
    Returns:
      "deliberation" — continue deliberation with next_speaker_id set in state
      "polling"      — budget exhausted or complete, move on to polling
    """
    game_state = state["game_state"]
    alive_agents = game_state.alive_agent_ids
    alive_count = len(alive_agents)
    max_messages = alive_count * 4

    # 1. Check budget exhaustion
    if game_state.deliberation_message_count >= max_messages:
        return "polling"

    # 2. Budget Reservation Check (Guarantee 2 turns)
    min_turns_needed = sum(
        max(0, 2 - game_state.turns_count.get(aid, 0)) for aid in alive_agents
    )
    remaining_budget = max_messages - game_state.deliberation_message_count
    is_must_speak_mode = remaining_budget <= min_turns_needed

    # Priority 1: Direct Rebuttal (Only if NOT in must-speak mode)
    last_msg = game_state.all_messages[-1] if game_state.all_messages else None
    if not is_must_speak_mode and last_msg and last_msg.phase == Phase.DELIBERATION:
        if (
            last_msg.intent in (DeliberationIntent.ACCUSE, DeliberationIntent.QUESTION)
            and last_msg.target_name
        ):
            # Resolve target_name to agent_id
            target_id = None
            for agent in game_state.config.agents:
                if agent.display_name.lower() == last_msg.target_name.lower():
                    target_id = agent.agent_id
                    break

            # Check for ping-pong loop (A -> B, B -> A, A -> B) to prevent 1v1 deadlocks
            delib_msgs = [
                m for m in game_state.all_messages if m.phase == Phase.DELIBERATION
            ]
            is_ping_pong = False
            if len(delib_msgs) >= 3:
                m1 = delib_msgs[-1]
                m2 = delib_msgs[-2]
                m3 = delib_msgs[-3]

                if (
                    m1.intent
                    in (DeliberationIntent.ACCUSE, DeliberationIntent.QUESTION)
                    and m2.intent
                    in (DeliberationIntent.ACCUSE, DeliberationIntent.QUESTION)
                    and m3.intent
                    in (DeliberationIntent.ACCUSE, DeliberationIntent.QUESTION)
                ):

                    def get_target_id(msg):
                        if not msg.target_name:
                            return None
                        for a in game_state.config.agents:
                            if a.display_name.lower() == msg.target_name.lower():
                                return a.agent_id
                        return None

                    id1, t1 = m1.agent_id, get_target_id(m1)
                    id2, t2 = m2.agent_id, get_target_id(m2)
                    id3, t3 = m3.agent_id, get_target_id(m3)

                    if id1 == t2 and t1 == id2 and id2 == t3 and t2 == id3:
                        is_ping_pong = True

            if target_id and target_id in alive_agents and target_id != last_msg.agent_id and not is_ping_pong:
                game_state.next_speaker_id = target_id
                return "deliberation"

    # Priority 2: Zero-turn agents
    zero_turn_agents = [
        aid for aid in alive_agents if game_state.turns_count.get(aid, 0) == 0
    ]
    if zero_turn_agents:
        game_state.next_speaker_id = random.choice(zero_turn_agents)
        return "deliberation"

    # Priority 3: One-turn agents
    one_turn_agents = [
        aid for aid in alive_agents if game_state.turns_count.get(aid, 0) == 1
    ]
    if one_turn_agents:
        game_state.next_speaker_id = random.choice(one_turn_agents)
        return "deliberation"

    # Priority 4: Free-for-all (budget remains, everyone has >= 2 turns)
    game_state.next_speaker_id = random.choice(alive_agents)
    return "deliberation"
