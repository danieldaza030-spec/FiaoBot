"""Provider abstraction for translating prompts into structured tool calls."""

from __future__ import annotations

# Abstract provider bases intentionally expose a single abstract method.
# pylint: disable=too-few-public-methods

from abc import ABC, abstractmethod

from fiadobot.prompting.types import PromptBundle

from .types import ToolCall


class LLMProvider(ABC):
    """Abstract base class for provider-specific LLM integrations."""

    @abstractmethod
    def interpret(self, prompt_bundle: PromptBundle) -> ToolCall:
        """Interpret a prepared prompt bundle and return a structured result."""
