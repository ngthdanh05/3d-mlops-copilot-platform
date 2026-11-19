import pytest

from app.schemas.copilot import ChatRequest
from app.services.copilot.engine import answer
from app.services.copilot.llm_client import LLMLocalError, LLMReply


@pytest.mark.parametrize("fail", [False, True])
@pytest.mark.parametrize("release_fails", [False, True])
async def test_engine_releases_on_success_or_error_and_preserves_reply(
    session, fail, release_fails
):
    class Client:
        released = 0

        async def complete(self, *args):
            if fail:
                raise LLMLocalError("offline runtime unavailable")
            return LLMReply(text="Xin chào")

        async def release(self):
            self.released += 1
            if release_fails:
                raise LLMLocalError("unload failed")

    client = Client()
    response = await answer(session, client, ChatRequest(message="chào"))
    assert client.released == 1
    assert "Ollama" in response.message if fail else response.message == "Xin chào"
