from src.models import GameState, Phase, PublicMessage, Role, RoundContext


class ContextBuilder:
    """
    Assembles a RoundContext for a given agent from the current GameState.

    The context is phase-aware:
    - SPEAKING:     public_history = messages from current round only
                    (SPEAKING phase only)
    - DELIBERATION: public_history = all messages from current round
                    (speaking + deliberation)
    - POLLING:      same as DELIBERATION
    - VOTING:       same as DELIBERATION
    - REACTION:     public_history = all messages from all rounds (full history)
    """

    @staticmethod
    def build(
        state: GameState,
        agent_id: str,
        is_final_round: bool = False,
    ) -> RoundContext:
        """
        Builds a RoundContext for the specified agent.

        Args:
            state: Current GameState. Must have current_phase set correctly.
            agent_id: The agent for whom to build the context.
            is_final_round: Whether this is the last round
                            (triggers warning in prompts).

        Returns:
            RoundContext with all fields populated for the agent.

        Raises:
            KeyError: if agent_id is not in state.role_assignments.
            ValueError: if state.current_phase is Phase.INIT or Phase.ENDGAME
                        (no context is built for non-interactive phases).
            AssertionError: if the agent is the Imposter but has a non-None secret word.
        """
        if agent_id not in state.role_assignments:
            raise KeyError(f"Agent ID '{agent_id}' not found in role assignments.")

        if state.current_phase in (Phase.INIT, Phase.ENDGAME):
            raise ValueError(
                f"Cannot build context for non-interactive phase: {state.current_phase}"
            )

        role_assignment = state.role_assignments[agent_id]

        # Imposter safety check
        if role_assignment.role == Role.IMPOSTER:
            assert role_assignment.secret_word is None, (
                f"Leak detected! Imposter agent '{agent_id}' "
                f"has a non-None secret word: {role_assignment.secret_word}"
            )

        public_history = ContextBuilder._get_public_history(state)
        alive_agents = ContextBuilder._format_alive_agents(state)

        # In current_phase DELIBERATION, we should use state.current_deliberation_round,
        # otherwise None or state.current_deliberation_round depending on the phase.
        delib_round = (
            state.current_deliberation_round
            if state.current_phase in (Phase.DELIBERATION, Phase.POLLING, Phase.VOTING)
            else None
        )

        all_agent_names = ", ".join(agent.display_name for agent in state.config.agents)
        game_language = state.config.game_language if hasattr(state.config, 'game_language') else "English"

        return RoundContext(
            role_assignment=role_assignment,
            current_phase=state.current_phase,
            current_round=state.current_round,
            deliberation_round=delib_round,
            public_history=public_history,
            announcements=state.all_announcements,
            alive_agents=alive_agents,
            all_agent_names=all_agent_names,
            game_language=game_language,
            is_final_round=is_final_round,
        )

    @staticmethod
    def _get_public_history(state: GameState) -> list[PublicMessage]:
        """
        Returns the correct subset of messages for the current phase.
        """
        phase = state.current_phase
        current_round = state.current_round

        if phase == Phase.SPEAKING:
            # Current round SPEAKING messages only
            return [
                m
                for m in state.all_messages
                if m.round_number == current_round and m.phase == Phase.SPEAKING
            ]
        elif phase in (Phase.DELIBERATION, Phase.POLLING, Phase.VOTING):
            # Speaking and Deliberation messages from current round
            return [
                m
                for m in state.all_messages
                if m.round_number == current_round
                and m.phase in (Phase.SPEAKING, Phase.DELIBERATION)
            ]
        elif phase == Phase.REACTION:
            # Full history across all rounds
            return state.all_messages

        return []

    @staticmethod
    def _format_alive_agents(state: GameState) -> list[dict[str, str]]:
        """
        Returns a list of dicts describing currently alive agents.
        Format: [{"agent_id": "agent_0", "display_name": "Alice"}, ...]
        Ordered by agent index (stable order, not turn order).
        """
        alive_list = []
        for agent in state.config.agents:
            if state.agent_alive.get(agent.agent_id, False):
                alive_list.append({
                    "agent_id": agent.agent_id,
                    "display_name": agent.display_name,
                })
        return alive_list
