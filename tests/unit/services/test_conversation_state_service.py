"""Unit tests for the conversation state service."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fiadobot.services.conversation_state_service import (
    CUSTOMER_DISAMBIGUATION_ACTION,
    ConversationStateService,
    PendingOption,
)
from fiadobot.services.exceptions import (
    DisambiguationOptionsError,
    NoPendingStateError,
    PendingActionNameTooLongError,
    PendingReplyNotResolvedError,
)


def test_start_customer_disambiguation_persists_options() -> None:
    """It should persist the pending customer options and context."""

    repository = MagicMock()
    repository.upsert_state.return_value = SimpleNamespace(chat_id=1)
    service = ConversationStateService(repository)

    options = [
        PendingOption(option_id=10, display_name="Juan Perez"),
        PendingOption(option_id=11, display_name="Juan Gomez"),
    ]
    pending_arguments = {"tool_name": "registrar_venta", "arguments": {}}

    service.start_customer_disambiguation(1, options, pending_arguments)

    repository.upsert_state.assert_called_once_with(
        1,
        CUSTOMER_DISAMBIGUATION_ACTION,
        {
            "options": [
                {"option_id": 10, "display_name": "Juan Perez"},
                {"option_id": 11, "display_name": "Juan Gomez"},
            ],
            "pending_arguments": pending_arguments,
        },
    )


def test_start_disambiguation_requires_at_least_two_options() -> None:
    """It should reject disambiguation flows with a single option."""

    service = ConversationStateService(MagicMock())

    with pytest.raises(DisambiguationOptionsError):
        service.start_disambiguation(
            1,
            CUSTOMER_DISAMBIGUATION_ACTION,
            [PendingOption(option_id=10, display_name="Juan Perez")],
            {},
        )


def test_start_disambiguation_rejects_long_action_name() -> None:
    """It should enforce the pending action column length."""

    service = ConversationStateService(MagicMock())

    with pytest.raises(PendingActionNameTooLongError):
        service.start_disambiguation(
            1,
            "x" * 51,
            [
                PendingOption(option_id=10, display_name="Juan Perez"),
                PendingOption(option_id=11, display_name="Juan Gomez"),
            ],
            {},
        )


def test_resolve_pending_reply_selects_option_and_clears_state() -> None:
    """It should resolve a numeric reply and delete the pending state."""

    repository = MagicMock()
    repository.get_by_chat_id.return_value = SimpleNamespace(
        pending_action=CUSTOMER_DISAMBIGUATION_ACTION,
        context={
            "options": [
                {"option_id": 10, "display_name": "Juan Perez"},
                {"option_id": 11, "display_name": "Juan Gomez"},
            ],
            "pending_arguments": {"tool_name": "registrar_venta"},
        },
    )
    service = ConversationStateService(repository)

    resolution = service.resolve_pending_reply(1, "la 2")

    assert resolution.pending_action == CUSTOMER_DISAMBIGUATION_ACTION
    assert resolution.selected_option.option_id == 11
    assert resolution.selected_option.display_name == "Juan Gomez"
    assert resolution.pending_arguments == {"tool_name": "registrar_venta"}
    repository.delete_state.assert_called_once_with(1)


def test_resolve_pending_reply_keeps_state_when_reply_is_invalid() -> None:
    """It should leave the state untouched if the reply cannot be resolved."""

    repository = MagicMock()
    repository.get_by_chat_id.return_value = SimpleNamespace(
        pending_action=CUSTOMER_DISAMBIGUATION_ACTION,
        context={
            "options": [
                {"option_id": 10, "display_name": "Juan Perez"},
                {"option_id": 11, "display_name": "Juan Gomez"},
            ],
            "pending_arguments": {"tool_name": "registrar_venta"},
        },
    )
    service = ConversationStateService(repository)

    with pytest.raises(PendingReplyNotResolvedError):
        service.resolve_pending_reply(1, "no sé")

    repository.delete_state.assert_not_called()


def test_resolve_pending_reply_raises_when_state_missing() -> None:
    """It should raise when there is no pending state for the chat."""

    repository = MagicMock()
    repository.get_by_chat_id.return_value = None
    service = ConversationStateService(repository)

    with pytest.raises(NoPendingStateError):
        service.resolve_pending_reply(1, "2")
