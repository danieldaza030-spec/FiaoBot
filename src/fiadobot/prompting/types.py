"""Data structures used to build provider-agnostic prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Canonical tool definition loaded from prompt assets.

    Args:
        name: Canonical tool name exposed to the LLM.
        description: Short human-readable description of the tool.
        parameters: JSON Schema fragment describing the tool arguments.
    """

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolSchema:
    """Container for the canonical tool definitions.

    Args:
        version: Schema version loaded from the prompt assets.
        tools: Ordered list of tool definitions.
    """

    version: str
    tools: list[ToolDefinition]


@dataclass(frozen=True, slots=True)
class PromptContext:
    """Runtime context used to assemble the final prompt.

    Args:
        user_message: Raw message sent by the user.
        conversational_context: Structured state used to continue a flow.
        locale: Locale code used to localize the prompt.
        channel: Source channel used for the interaction.
    """

    user_message: str
    conversational_context: dict[str, Any] = field(default_factory=dict)
    locale: str = "es"
    channel: str = "telegram"


@dataclass(frozen=True, slots=True)
class PromptBundle:
    """Final prompt payload ready to be passed to an LLM provider.

    Args:
        system_prompt: Raw system prompt loaded from disk.
        user_message: User message forwarded to the provider.
        rendered_system_prompt: System prompt enriched with runtime context.
        tools: Canonical tool schema loaded from disk.
        conversational_context: Structured state needed by the flow.
        source_paths: Optional paths used to build the bundle.
    """

    system_prompt: str
    user_message: str
    rendered_system_prompt: str
    tools: ToolSchema
    conversational_context: dict[str, Any] = field(default_factory=dict)
    source_paths: tuple[Path, Path] | None = None
