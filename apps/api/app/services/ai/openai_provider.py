import httpx

from app.core.config import get_settings
from app.services.ai.llm_provider import LLMProvider
from app.services.ai.mock_provider import MockLLMProvider


class OpenAILLMProvider(LLMProvider):
    """Real OpenAI-compatible text generation. Voice transcription and image
    analysis are delegated to the mock provider until those endpoints are
    wired and tested against real credentials (see module docstring in
    llm_provider.py)."""

    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self.version = settings.openai_model
        self._fallback = MockLLMProvider()

    def generate_text(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = httpx.post(
            f"{self._settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.openai_api_key}"},
            json={"model": self._settings.openai_model, "messages": messages, "temperature": 0.2},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def transcribe_audio(self, file_path: str) -> str:
        return self._fallback.transcribe_audio(file_path)

    def analyze_image(self, file_path: str) -> list[tuple[str, float]]:
        return self._fallback.analyze_image(file_path)
