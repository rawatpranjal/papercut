"""LLM client wrapper using litellm."""

import os
from dataclasses import dataclass

from papercutter.exceptions import PapercutterError


class LLMNotAvailableError(PapercutterError):
    """Raised when LLM features are not available."""

    def __init__(self, message: str = "LLM features require an API key"):
        super().__init__(message, "Set PAPERCUTTER_API_KEY or ANTHROPIC_API_KEY env var")


class LLMError(PapercutterError):
    """Raised when LLM call fails."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details)


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMClient:
    """Wrapper around litellm for LLM calls.

    Supports multiple providers through litellm:
    - Anthropic (claude-sonnet-4-20250514, etc.)
    - OpenAI (gpt-4o, etc.)
    - Others supported by litellm
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """Initialize the LLM client.

        Args:
            api_key: API key (defaults to env var).
            model: Model to use (defaults to env var or claude-sonnet-4-20250514).
        """
        self.api_key = api_key or self._get_api_key()
        self.model = model or os.environ.get("PAPERCUTTER_MODEL", self.DEFAULT_MODEL)
        self._litellm = None

    def _get_api_key(self) -> str | None:
        """Get API key from environment."""
        # Check in order of preference
        for var in ["PAPERCUTTER_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
            if key := os.environ.get(var):
                return key
        return None

    def _ensure_litellm(self) -> None:
        """Ensure litellm is available and configured."""
        if self._litellm is not None:
            return

        try:
            import litellm

            self._litellm = litellm
        except ImportError:
            raise LLMNotAvailableError(
                "LLM features require litellm. Install with: pip install papercutter[llm]"
            )

        if not self.api_key:
            raise LLMNotAvailableError()

        # Note: API key is passed directly to completion() calls
        # to avoid exposing it in environment variables

    def is_available(self) -> bool:
        """Check if LLM features are available."""
        try:
            self._ensure_litellm()
            return True
        except LLMNotAvailableError:
            return False

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> LLMResponse:
        """Send a completion request to the LLM.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with the completion.

        Raises:
            LLMNotAvailableError: If LLM is not configured.
            LLMError: If the LLM call fails.
        """
        self._ensure_litellm()
        assert self._litellm is not None  # Type narrowing for mypy

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._litellm.completion(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=self.api_key,  # Pass directly, don't use environ
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        except Exception as e:
            raise LLMError(f"LLM call failed: {e}", str(e))

    def stream(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ):
        """Stream a completion response from the LLM.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Yields:
            String chunks of the response.

        Raises:
            LLMNotAvailableError: If LLM is not configured.
            LLMError: If the LLM call fails.
        """
        self._ensure_litellm()
        assert self._litellm is not None  # Type narrowing for mypy

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._litellm.completion(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                api_key=self.api_key,  # Pass directly, don't use environ
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise LLMError(f"LLM stream failed: {e}", str(e))


# Singleton client instance
_client: LLMClient | None = None


def get_client(
    api_key: str | None = None,
    model: str | None = None,
) -> LLMClient:
    """Get or create the LLM client.

    Args:
        api_key: Optional API key override.
        model: Optional model override.

    Returns:
        LLMClient instance.
    """
    global _client

    # Create new client if parameters provided or no client exists
    if api_key or model or _client is None:
        _client = LLMClient(api_key=api_key, model=model)

    return _client
