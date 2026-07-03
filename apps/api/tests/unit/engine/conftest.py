import pytest
import fakeredis
from src.core.redis import RedisClient


class MockAgent:
    """
    Test double for BaseAgent that returns configurable outputs.
    """

    def __init__(self, speak_outputs: list | None = None, vote_outputs: list | None = None):
        """
        Args:
            speak_outputs: List of return values in call order.
                           Each can be an output model, an Exception (to raise),
                           or None.
            vote_outputs: List of return values in call order.
                          Each can be an output model, an Exception (to raise),
                          or None.
        """
        self._speak_outputs = iter(speak_outputs or [])
        self._vote_outputs = iter(vote_outputs or [])
        self.speak_calls: list[dict] = []
        self.vote_calls: list[dict] = []

    async def speak(self, context):
        self.speak_calls.append({"context": context})
        result = next(self._speak_outputs)
        if isinstance(result, Exception):
            raise result
        return result

    async def vote(self, context):
        self.vote_calls.append({"context": context})
        result = next(self._vote_outputs)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def fake_redis():
    return fakeredis.FakeAsyncRedis()


@pytest.fixture
def fake_redis_client(fake_redis):
    return RedisClient(fake_redis)
