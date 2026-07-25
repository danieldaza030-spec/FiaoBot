"""Internal LLM data structures used across providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Structured output returned by an LLM provider."""

    tool_name: str | None
    arguments: dict[str, Any] = field(default_factory=dict)
    assistant_message: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    missing_fields: list[str] = field(default_factory=list)
