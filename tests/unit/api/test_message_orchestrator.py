"""Unit tests for MessageOrchestrator's handling of LLM provider failures."""

from __future__ import annotations

from unittest.mock import MagicMock

from fiadobot.api.message_orchestrator import (
    MessageOrchestrator,
    _PROVIDER_ERROR_MESSAGE,
)
from fiadobot.llm.exceptions import LLMProviderError


def test_handle_message_returns_friendly_reply_on_provider_failure() -> None:
    """It should return a friendly message when the LLM provider fails."""

    mock_service_context = MagicMock()
    mock_service_context.conversation_state_service.has_pending_state.return_value = (
        False
    )

    mock_prompt_builder = MagicMock()
    mock_prompt_builder.build.return_value = MagicMock()

    mock_llm_provider = MagicMock()
    mock_llm_provider.interpret.side_effect = LLMProviderError("boom")

    orchestrator = MessageOrchestrator(
        mock_service_context, mock_prompt_builder, mock_llm_provider
    )

    reply = orchestrator.handle_message(chat_id=1, text="hola")

    assert reply == _PROVIDER_ERROR_MESSAGE
