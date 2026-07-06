import pytest

from src.agents.human_agent import HumanAgent
from src.models import AgentType


def test_human_agent_raises_not_implemented(make_agent_config, role_assignments):
    """Verify that HumanAgent raises NotImplementedError for all phase methods."""
    config = make_agent_config(1, AgentType.HUMAN)
    role_assignment = role_assignments["agent_1"]
    agent = HumanAgent(config=config, role_assignment=role_assignment)

    with pytest.raises(NotImplementedError, match="Human agents are out of scope for Sprint 1"):
        import asyncio
        asyncio.run(agent.speak(context=None))

    with pytest.raises(NotImplementedError, match="Human agents are out of scope for Sprint 1"):
        import asyncio
        asyncio.run(agent.deliberate(context=None))

    with pytest.raises(NotImplementedError, match="Human agents are out of scope for Sprint 1"):
        import asyncio
        asyncio.run(agent.poll(context=None))

    with pytest.raises(NotImplementedError, match="Human agents are out of scope for Sprint 1"):
        import asyncio
        asyncio.run(agent.vote(context=None))

    with pytest.raises(NotImplementedError, match="Human agents are out of scope for Sprint 1"):
        import asyncio
        asyncio.run(agent.react(context=None))
