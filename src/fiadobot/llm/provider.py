"""Provider abstraction for translating prompts into structured tool calls."""

from __future__ import annotations

# Abstract provider bases intentionally expose a single abstract method.
# pylint: disable=too-few-public-methods

from abc import ABC, abstractmethod

from fiadobot.prompting.types import PromptBundle

from .types import ToolCall


class LLMProvider(ABC):
    """Abstract base class for provider-specific LLM integrations.

    Implementations receive a prepared prompt bundle and return a normalized
    tool call regardless of the underlying vendor API.
    """

    @abstractmethod
    def interpret(self, prompt_bundle: PromptBundle) -> ToolCall:
        """Interpret a prepared prompt bundle and return a structured result.

        Args:
            prompt_bundle: Fully assembled prompt payload produced by the builder.

        Returns:
            The normalized tool call returned by the provider.

        Raises:
            LLMProviderError: If the underlying provider fails to produce a
                usable response.
        """
