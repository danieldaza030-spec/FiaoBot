"""Factory for selecting the configured LLM provider implementation.

The rest of the backend only depends on the ``LLMProvider`` abstraction; this
module is the single place that knows how to translate configuration into a
concrete adapter, so switching providers never touches business logic.
"""

from __future__ import annotations

from fiadobot.config import AppConfig

from .openai_provider import OpenAIProvider
from .provider import LLMProvider

_SUPPORTED_PROVIDERS = ("openai",)


def create_llm_provider(config: AppConfig) -> LLMProvider:
    """Instantiate the configured LLM provider implementation.

    Args:
        config: Application configuration holding provider settings.

    Returns:
        A configured LLM provider ready to interpret prompt bundles.

    Raises:
        ValueError: If the configured provider name is not supported.
    """

    provider_name = config.llm_provider.strip().lower()
    if provider_name == "openai":
        return OpenAIProvider.from_api_key(
            model=config.openai_model,
            api_key=config.openai_api_key,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{config.llm_provider}'. "
        f"Supported providers: {', '.join(_SUPPORTED_PROVIDERS)}."
    )
