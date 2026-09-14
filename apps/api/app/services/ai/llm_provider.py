"""Pluggable LLM abstraction (section 36/55). `get_llm_provider()` returns a
`MockLLMProvider` (deterministic, clearly DEMO-labeled output, no external
calls) unless OPENAI_API_KEY is set in the environment, in which case text
generation is routed to a real OpenAI-compatible endpoint.

Voice transcription and image object-detection stay on the mock implementation
in this build regardless of provider - wiring real Whisper/vision endpoints is
future work (section 55: don't fake integrations that aren't actually
connected) and would need real credentials to test.
"""

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings


class LLMProvider(ABC):
    name: str
    version: str

    @abstractmethod
    def generate_text(self, prompt: str, system: str | None = None) -> str: ...

    @abstractmethod
    def transcribe_audio(self, file_path: str) -> str: ...

    @abstractmethod
    def analyze_image(self, file_path: str) -> list[tuple[str, float]]: ...


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.ai_enabled_real_provider:
        from app.services.ai.openai_provider import OpenAILLMProvider

        return OpenAILLMProvider()
    from app.services.ai.mock_provider import MockLLMProvider

    return MockLLMProvider()
