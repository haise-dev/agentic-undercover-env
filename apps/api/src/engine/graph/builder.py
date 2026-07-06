from langgraph.graph import END, START, StateGraph

from src.engine.event_emitter import EventEmitter
from src.engine.graph.routers import poll_router
from src.engine.graph.state import GraphState
from src.engine.nodes.deliberation_node import deliberation_node
from src.engine.nodes.polling_node import polling_node
from src.engine.nodes.reaction_node import reaction_node
from src.engine.nodes.speaking_node import speaking_node
from src.engine.nodes.voting_node import voting_node
from src.models import Phase


def build_graph(agents: dict, emitter: EventEmitter):
    """
    Builds and compiles the full LangGraph state machine.
    """
    workflow = StateGraph(GraphState)

    async def speaking_wrapper(state: GraphState) -> GraphState:
        return await speaking_node(state, agents, emitter)

    async def deliberation_wrapper(state: GraphState) -> GraphState:
        return await deliberation_node(state, agents, emitter)

    async def polling_wrapper(state: GraphState) -> GraphState:
        return await polling_node(state, agents, emitter)

    async def voting_wrapper(state: GraphState) -> GraphState:
        game_state = state["game_state"]
        game_state.current_phase = Phase.VOTING
        await voting_node(game_state, agents, emitter)
        return state

    async def reaction_wrapper(state: GraphState) -> GraphState:
        game_state = state["game_state"]
        game_state.current_phase = Phase.REACTION
        await reaction_node(game_state, agents, emitter)
        return state

    # Add all nodes
    workflow.add_node("speaking", speaking_wrapper)
    workflow.add_node("deliberation", deliberation_wrapper)
    workflow.add_node("polling", polling_wrapper)
    workflow.add_node("voting", voting_wrapper)
    workflow.add_node("reaction", reaction_wrapper)

    # Wire nodes
    workflow.add_edge(START, "speaking")
    workflow.add_edge("speaking", "deliberation")
    workflow.add_edge("deliberation", "polling")

    # Conditional edge
    workflow.add_conditional_edges(
        "polling",
        poll_router,
        {
            "voting_node": "voting",
            "speaking_node": "speaking",
        },
    )

    workflow.add_edge("voting", "reaction")
    workflow.add_edge("reaction", END)

    return workflow.compile()
