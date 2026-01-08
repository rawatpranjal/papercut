"""LLM client wrapper using litellm for multi-provider support."""

from functools import lru_cache
from typing import Any, Optional

from papercutter.config import get_settings
from papercutter.exceptions import LLMError, MissingAPIKeyError

# Try to import litellm, provide helpful error if not installed
try:
    import litellm
    from litellm import completion

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    litellm = None
    completion = None


class LLMClient:
    """Unified LLM client supporting multiple providers via litellm."""

    # Model aliases for convenience
    MODEL_ALIASES = {
        "claude": "claude-sonnet-4-20250514",
        "claude-sonnet": "claude-sonnet-4-20250514",
        "claude-opus": "claude-opus-4-20250514",
        "claude-haiku": "claude-3-5-haiku-20241022",
        "gpt4": "gpt-4o",
        "gpt4o": "gpt-4o",
        "gpt4-mini": "gpt-4o-mini",
    }

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Initialize LLM client.

        Args:
            model: Model name or alias. Defaults to settings.
            temperature: Sampling temperature. Defaults to settings.
            max_tokens: Maximum tokens in response. Defaults to settings.

        Raises:
            LLMError: If litellm is not installed.
        """
        if not LITELLM_AVAILABLE:
            raise LLMError(
                "LLM features require litellm",
                details="Install with: pip install papercutter[llm]",
            )

        settings = get_settings()

        # Resolve model alias
        model = model or settings.llm.default_model
        self.model = self.MODEL_ALIASES.get(model, model)

        self.temperature = temperature if temperature is not None else settings.llm.temperature
        self.max_tokens = max_tokens or settings.llm.max_tokens

        # Configure API keys from settings/environment
        self._configure_api_keys()

    def _configure_api_keys(self) -> None:
        """Set up API keys from settings or environment."""
        settings = get_settings()

        # litellm reads from environment variables by default:
        # ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.
        # We can also set them explicitly if provided in settings

        if settings.anthropic_api_key:
            import os

            os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)

        if settings.openai_api_key:
            import os

            os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a completion from the LLM.

        Args:
            prompt: User prompt/message.
            system: Optional system prompt.
            **kwargs: Additional arguments passed to litellm.

        Returns:
            Generated text response.

        Raises:
            MissingAPIKeyError: If API key not configured.
            LLMError: If completion fails.
        """
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        try:
            response = completion(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                **{k: v for k, v in kwargs.items() if k not in ("temperature", "max_tokens")},
            )

            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e).lower()

            if "api key" in error_str or "authentication" in error_str:
                raise MissingAPIKeyError(
                    f"API key not configured for {self.model}",
                    details="Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable",
                ) from e

            raise LLMError(
                f"LLM completion failed: {e}",
                details=f"Model: {self.model}",
            ) from e

    def complete_structured(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_format: Optional[dict] = None,
        **kwargs: Any,
    ) -> str:
        """Generate a structured (JSON) completion.

        Args:
            prompt: User prompt requesting structured output.
            system: Optional system prompt.
            response_format: JSON schema for response (if supported by model).
            **kwargs: Additional arguments.

        Returns:
            JSON string response.
        """
        # Add JSON instruction to system prompt
        json_system = (system or "") + "\n\nRespond with valid JSON only. No other text."

        return self.complete(prompt, system=json_system.strip(), **kwargs)


@lru_cache
def get_client(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LLMClient:
    """Get a cached LLM client instance.

    Args:
        model: Model name or alias.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens.

    Returns:
        LLMClient instance.
    """
    return LLMClient(model=model, temperature=temperature, max_tokens=max_tokens)


def check_llm_available() -> bool:
    """Check if LLM features are available.

    Returns:
        True if litellm is installed.
    """
    return LITELLM_AVAILABLE
