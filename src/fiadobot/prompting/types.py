"""Data structures used to build provider-agnostic prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Canonical tool definition loaded from prompt assets."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolSchema:
    """Container for the canonical tool definitions."""

    version: str
    tools: list[ToolDefinition]


@dataclass(frozen=True, slots=True)
class PromptContext:
    """Runtime context used to assemble the final prompt."""

    user_message: str
    conversational_context: dict[str, Any] = field(default_factory=dict)
    locale: str = "es"
    channel: str = "telegram"


@dataclass(frozen=True, slots=True)
class PromptBundle:
    """Final prompt payload ready to be passed to an LLM provider."""

    system_prompt: str
    user_message: str
    rendered_system_prompt: str
    tools: ToolSchema
    conversational_context: dict[str, Any] = field(default_factory=dict)
    source_paths: tuple[Path, Path] | None = None
