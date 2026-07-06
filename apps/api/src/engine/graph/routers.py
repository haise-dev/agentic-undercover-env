from src.engine.graph.state import GraphState


def poll_router(state: GraphState) -> str:
    """
    Conditional routing logic after polling_node.
    If proceed_to_vote is True, route to voting_node.
    Otherwise, loop back to speaking_node (for the next round).
    """
    if state.get("proceed_to_vote"):
        return "voting_node"
    return "speaking_node"
