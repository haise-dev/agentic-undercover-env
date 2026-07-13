from src.agents.prompt_templates import (
    IMPOSTER_DELIBERATION_PROMPT,
    IMPOSTER_SPEAKING_PROMPT,
    IMPOSTER_SYSTEM_PROMPT,
    POLLING_PHASE_PROMPT,
    REACTION_ELIMINATED_PROMPT,
    REACTION_SURVIVOR_PROMPT,
    SPEAKING_PHASE_PROMPT,
    VILLAGER_DELIBERATION_PROMPT,
    VILLAGER_SYSTEM_PROMPT,
    VOTING_PHASE_PROMPT,
)
from src.models import AgentRoleAssignment, Phase, PublicMessage, Role, RoundContext


def format_alive_agents(alive_agents: list[dict[str, str]]) -> str:
    """Formats a comma-separated list of alive agents' display names."""
    return ", ".join([agent.get("display_name", "") for agent in alive_agents])


def format_chat_history(messages: list[PublicMessage]) -> str:
    """Formats public messages into [Round X - Phase] [DisplayName]: Content lines."""
    if not messages:
        return ""
    formatted = []
    for msg in messages:
        phase_str = "Guess" if msg.phase == Phase.SPEAKING else "Discuss"
        formatted.append(
            f"[Round {msg.round_number} - {phase_str}] [{msg.display_name}]: {msg.content}"
        )
    return "\n".join(formatted)


def build_system_prompt(
    role_assignment: AgentRoleAssignment,
    display_name: str,
    agent_names_list: str,
    game_language: str,
) -> str:
    """Builds the fixed persona system prompt block based on role."""
    if role_assignment.role == Role.VILLAGER:
        template = VILLAGER_SYSTEM_PROMPT
        # Ensure secret_word is provided for Villager
        secret_word = role_assignment.secret_word or "[UNKNOWN]"
        return template.format(
            agent_name=display_name,
            topic=role_assignment.topic,
            secret_word=secret_word,
            agent_names_list=agent_names_list,
            game_language=game_language,
        )
    elif role_assignment.role == Role.IMPOSTER:
        template = IMPOSTER_SYSTEM_PROMPT
        # Secret word is intentionally completely omitted
        return template.format(
            agent_name=display_name,
            topic=role_assignment.topic,
            agent_names_list=agent_names_list,
            game_language=game_language,
        )
    else:
        raise ValueError(f"Unsupported role: {role_assignment.role}")


def build_user_prompt(
    phase: Phase, context: RoundContext, current_agent_name: str, **kwargs
) -> str:
    """Builds the phase-specific dynamic context block (user prompt)."""
    alive_agents_list = format_alive_agents(context.alive_agents)

    # Separate history into past rounds and current round events
    past_history_msgs = [
        m for m in context.public_history if m.round_number < context.current_round
    ]
    current_chat_msgs = [
        m
        for m in context.public_history
        if m.round_number == context.current_round and m.phase == Phase.SPEAKING
    ]
    current_delib_msgs = [
        m
        for m in context.public_history
        if m.round_number == context.current_round and m.phase == Phase.DELIBERATION
    ]

    past_history = format_chat_history(past_history_msgs)
    chat_history = format_chat_history(current_chat_msgs)
    deliberation_history = format_chat_history(current_delib_msgs)

    format_kwargs = {
        "round_number": context.current_round,
        "deliberation_round": context.deliberation_round,
        "alive_agents_list": alive_agents_list,
        "past_history": past_history,
        "chat_history": chat_history,
        "deliberation_history": deliberation_history,
        "game_language": context.game_language,
        "is_final_round_notice": "This is the FINAL ROUND. A vote will be forced after deliberation."
        if context.is_final_round
        else "",
        "topic": context.role_assignment.topic,
        "secret_word": context.role_assignment.secret_word or "",
    }

    if phase == Phase.SPEAKING:
        if context.role_assignment.role == Role.IMPOSTER:
            return IMPOSTER_SPEAKING_PROMPT.format(**format_kwargs)
        else:
            return SPEAKING_PHASE_PROMPT.format(**format_kwargs)

    elif phase == Phase.DELIBERATION:
        if context.role_assignment.role == Role.IMPOSTER:
            return IMPOSTER_DELIBERATION_PROMPT.format(**format_kwargs)
        else:
            return VILLAGER_DELIBERATION_PROMPT.format(**format_kwargs)

    elif phase == Phase.POLLING:
        return POLLING_PHASE_PROMPT.format(**format_kwargs)

    elif phase == Phase.VOTING:
        return VOTING_PHASE_PROMPT.format(**format_kwargs)

    elif phase == Phase.REACTION:
        is_eliminated_agent = kwargs.get("is_eliminated_agent", False)

        if is_eliminated_agent:
            return REACTION_ELIMINATED_PROMPT.format(
                agent_name=current_agent_name, game_language=context.game_language
            )
        else:
            eliminated_role = kwargs.get("eliminated_role", "unknown")
            if isinstance(eliminated_role, Role):
                eliminated_role = eliminated_role.value

            agent_vote_target = kwargs.get("agent_vote_target", "unknown")
            game_outcome = kwargs.get("game_outcome", "unknown")

            return REACTION_SURVIVOR_PROMPT.format(
                agent_name=current_agent_name,
                eliminated_agent_name=kwargs.get("eliminated_agent_name", ""),
                eliminated_role=eliminated_role,
                outcome_statement=kwargs.get("outcome_statement", ""),
                last_words=kwargs.get("last_words", ""),
                agent_vote_target=agent_vote_target,
                game_outcome=game_outcome,
                vote_correct_status=kwargs.get("vote_correct_status", "unknown"),
                you_won_status=kwargs.get("you_won_status", "unknown"),
                game_language=context.game_language,
            )

    else:
        raise ValueError(f"Unsupported phase for user prompt: {phase}")
