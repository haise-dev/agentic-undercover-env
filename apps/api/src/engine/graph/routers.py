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
            if target_id and target_id in alive_agents:
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
