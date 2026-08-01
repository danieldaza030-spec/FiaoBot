"""Internal LLM data structures used across providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Structured output returned by an LLM provider.

    Args:
        tool_name: Name of the selected tool, if any.
        arguments: JSON-compatible arguments required by the tool.
        assistant_message: Optional short message to show to the user.
        needs_clarification: Whether the flow requires more data.
        clarification_question: Clarifying question to ask the user.
        missing_fields: Fields that are still missing from the request.
    """

    tool_name: str | None
    arguments: dict[str, Any] = field(default_factory=dict)
    assistant_message: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    missing_fields: list[str] = field(default_factory=list)
