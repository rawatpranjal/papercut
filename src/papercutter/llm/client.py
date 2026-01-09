"""LLM client wrapper using litellm."""

import base64
import os
import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from papercutter.config.settings import get_settings
from papercutter.exceptions import PapercutterError

if TYPE_CHECKING:
    from pydantic import BaseModel

    T = TypeVar("T", bound=BaseModel)
else:
    T = TypeVar("T")


class LLMNotAvailableError(PapercutterError):
    """Raised when LLM features are not available."""

    def __init__(self, message: str = "LLM features require an API key"):
        super().__init__(
            message,
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY env var, "
            "or add to ~/.papercutter/config.yaml:\n"
            "  anthropic_api_key: sk-...\n"
            "  # or: openai_api_key: sk-..."
        )


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
    cost_usd: float | None = None  # Estimated cost if available


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
            api_key: API key (defaults to env var, then config file).
            model: Model to use (defaults to env var, then config file, then default).
        """
        self.api_key = api_key or self._get_api_key()
        self.model = model or self._get_model()
        self._litellm: types.ModuleType | None = None

    def _get_api_key(self) -> str | None:
        """Get API key from environment or config file.

        Checks in order:
        1. Environment variables (PAPERCUTTER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY)
        2. Config file (~/.papercutter/config.yaml)
        """
        # Check environment variables first
        for var in ["PAPERCUTTER_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
            if key := os.environ.get(var):
                return key

        # Check config file
        settings = get_settings()
        if settings.anthropic_api_key:
            return settings.anthropic_api_key
        if settings.openai_api_key:
            return settings.openai_api_key

        return None

    def _get_model(self) -> str:
        """Get model from environment or config file.

        Checks in order:
        1. Environment variable (PAPERCUTTER_MODEL)
        2. Config file (~/.papercutter/config.yaml)
        3. Default model
        """
        # Check environment variable first
        if model := os.environ.get("PAPERCUTTER_MODEL"):
            return model

        # Check config file
        settings = get_settings()
        return settings.llm.default_model

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

    def complete_vision(
        self,
        prompt: str,
        images: list[bytes],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> LLMResponse:
        """Send a vision completion request with images.

        Args:
            prompt: The user prompt.
            images: List of image bytes (PNG format).
            system: Optional system prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
            model: Override model (defaults to gpt-4o-mini for vision).

        Returns:
            LLMResponse with the completion.

        Raises:
            LLMNotAvailableError: If LLM is not configured.
            LLMError: If the LLM call fails.
        """
        self._ensure_litellm()
        assert self._litellm is not None

        # Default to gpt-4o-mini for vision (cost-effective)
        vision_model = model or "gpt-4o-mini"

        # Build content with text and images
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images:
            b64 = base64.b64encode(img).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})

        try:
            response = self._litellm.completion(
                model=vision_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=self.api_key,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                cost_usd=self._estimate_cost(
                    vision_model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                ),
            )

        except Exception as e:
            raise LLMError(f"Vision LLM call failed: {e}", str(e))

    def complete_structured(
        self,
        prompt: str,
        response_model: type[T],
        images: list[bytes] | None = None,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        model: str | None = None,
    ) -> T:
        """Get structured output conforming to a Pydantic model.

        Uses the instructor library for reliable structured outputs.

        Args:
            prompt: The user prompt.
            response_model: Pydantic model class for response schema.
            images: Optional list of image bytes (PNG format).
            system: Optional system prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (lower for structured).
            model: Override model (defaults to gpt-4o-mini for vision).

        Returns:
            Instance of response_model populated from LLM response.

        Raises:
            LLMNotAvailableError: If LLM is not configured.
            LLMError: If the LLM call fails or parsing fails.
        """
        self._ensure_litellm()
        assert self._litellm is not None

        try:
            import instructor
        except ImportError:
            raise LLMNotAvailableError(
                "Structured outputs require instructor. "
                "Install with: pip install instructor"
            )

        # Use vision model if images provided
        structured_model = model or ("gpt-4o-mini" if images else self.model)

        # Build content
        if images:
            content: list[dict] = [{"type": "text", "text": prompt}]
            for img in images:
                b64 = base64.b64encode(img).decode("utf-8")
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })
        else:
            content = prompt  # type: ignore

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})

        try:
            # Create instructor-wrapped client
            client = instructor.from_litellm(self._litellm.completion)

            return client(
                model=structured_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=self.api_key,
                response_model=response_model,
            )

        except Exception as e:
            raise LLMError(f"Structured LLM call failed: {e}", str(e))

    def _estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float | None:
        """Estimate cost in USD for a completion.

        Args:
            model: Model name.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD, or None if unknown model.
        """
        # Approximate costs per 1M tokens (as of 2024)
        costs = {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        }

        # Find matching model (handle versioned names)
        pricing = None
        for name, prices in costs.items():
            if name in model or model in name:
                pricing = prices
                break

        if not pricing:
            return None

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)


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
