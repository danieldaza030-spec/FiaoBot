"""Service for managing pending conversational state and disambiguation flows.

The service is intentionally generic: any backend flow that needs the vendor
to disambiguate between multiple candidates (customers today, potentially
other entities later) can reuse it by providing a distinct
``pending_action`` name. It never decides business logic; it only stores and
retrieves the minimal context required to resume a flow (RF08, RNF02).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from fiadobot.models.conversation_state import ConversationState
from fiadobot.repositories.conversation_state_repository import (
    ConversationStateRepository,
)

from .exceptions import (
    DisambiguationOptionsError,
    NoPendingStateError,
    PendingActionNameTooLongError,
    PendingReplyNotResolvedError,
)

#: Name used for the customer disambiguation flow described in RF08.
CUSTOMER_DISAMBIGUATION_ACTION = "desambiguar_cliente"

#: Matches the `estado_conversacion.accion_pendiente` column size.
_MAX_PENDING_ACTION_LENGTH = 50

#: Extracts the first integer found in a free-form reply (e.g. "el 2" -> 2).
_OPTION_INDEX_PATTERN = re.compile(r"\d+")


@dataclass(frozen=True, slots=True)
class PendingOption:
    """One selectable candidate offered to the vendor.

    Args:
        option_id: Identifier of the underlying entity (e.g. a customer id).
        display_name: Human-readable label shown to the vendor.
    """

    option_id: int
    display_name: str


@dataclass(frozen=True, slots=True)
class PendingResolution:
    """Result of resolving a pending conversational reply.

    Args:
        pending_action: Name of the action that was pending.
        selected_option: Candidate chosen by the vendor.
        pending_arguments: Original arguments needed to resume the flow.
    """

    pending_action: str
    selected_option: PendingOption
    pending_arguments: dict[str, Any] = field(default_factory=dict)


class ConversationStateService:
    """Coordinate pending conversational flows for Telegram chats.

    Args:
        conversation_state_repository: Repository used to persist and load
            pending conversational state.
    """

    def __init__(
        self, conversation_state_repository: ConversationStateRepository
    ) -> None:
        """Initialize the service with its repository dependency.

        Args:
            conversation_state_repository: Repository used for persistence.

        Returns:
            None.

        Raises:
            None.
        """

        self.conversation_state_repository = conversation_state_repository

    def has_pending_state(self, chat_id: int) -> bool:
        """Return whether a chat currently has a pending flow.

        Args:
            chat_id: Telegram chat identifier to check.

        Returns:
            ``True`` when the chat has a pending state, otherwise ``False``.
        """

        return self.conversation_state_repository.get_by_chat_id(chat_id) is not None

    def get_pending_action(self, chat_id: int) -> str | None:
        """Return the pending action name for a chat, if any.

        Args:
            chat_id: Telegram chat identifier to check.

        Returns:
            The pending action name, or ``None`` when there is no active flow.
        """

        state = self.conversation_state_repository.get_by_chat_id(chat_id)
        return state.pending_action if state is not None else None

    def start_disambiguation(
        self,
        chat_id: int,
        pending_action: str,
        options: Sequence[PendingOption],
        pending_arguments: dict[str, Any],
    ) -> ConversationState:
        """Persist a disambiguation flow waiting for the vendor to choose.

        Args:
            chat_id: Telegram chat identifier that owns the pending flow.
            pending_action: Name identifying the kind of pending flow.
            options: Candidates the vendor must choose from.
            pending_arguments: Original arguments needed to resume the flow
                once the vendor picks an option.

        Returns:
            The persisted conversation state.

        Raises:
            DisambiguationOptionsError: If fewer than two options are given.
            PendingActionNameTooLongError: If the action name is too long to
                be stored in the `estado_conversacion` table.
            SQLAlchemyError: If the insert or commit fails.
        """

        if len(pending_action) > _MAX_PENDING_ACTION_LENGTH:
            raise PendingActionNameTooLongError(
                f"Pending action name must be at most {_MAX_PENDING_ACTION_LENGTH} "
                "characters long."
            )

        if len(options) < 2:
            raise DisambiguationOptionsError(
                "Disambiguation requires at least two candidate options."
            )

        context = {
            "options": [
                {"option_id": option.option_id, "display_name": option.display_name}
                for option in options
            ],
            "pending_arguments": pending_arguments,
        }
        return self.conversation_state_repository.upsert_state(
            chat_id, pending_action, context
        )

    def start_customer_disambiguation(
        self,
        chat_id: int,
        candidates: Sequence[PendingOption],
        pending_arguments: dict[str, Any],
    ) -> ConversationState:
        """Persist a customer disambiguation flow for a chat (RF08).

        Args:
            chat_id: Telegram chat identifier that owns the pending flow.
            candidates: Customer candidates the vendor must choose from.
            pending_arguments: Original tool arguments needed to resume the
                flow once the customer is resolved.

        Returns:
            The persisted conversation state.

        Raises:
            DisambiguationOptionsError: If fewer than two candidates are given.
            SQLAlchemyError: If the insert or commit fails.
        """

        return self.start_disambiguation(
            chat_id, CUSTOMER_DISAMBIGUATION_ACTION, candidates, pending_arguments
        )

    def resolve_pending_reply(self, chat_id: int, reply_text: str) -> PendingResolution:
        """Resolve a vendor reply against the pending options for a chat.

        Only a numeric option index (e.g. "2" or "el 2") is accepted. The
        pending state is deleted once it is successfully resolved.

        Args:
            chat_id: Telegram chat identifier replying to a pending question.
            reply_text: Raw text sent by the vendor.

        Returns:
            The resolved option together with the original pending arguments.

        Raises:
            NoPendingStateError: If the chat has no pending state.
            PendingReplyNotResolvedError: If the reply does not match any of
                the pending options. The pending state is kept untouched so
                the backend can ask the vendor to reply again.
            SQLAlchemyError: If the delete or commit fails.
        """

        state = self.conversation_state_repository.get_by_chat_id(chat_id)
        if state is None:
            raise NoPendingStateError(f"Chat {chat_id} has no pending state.")

        options = state.context.get("options", [])
        selected = self._match_option_by_index(reply_text, options)
        if selected is None:
            raise PendingReplyNotResolvedError(
                "The reply did not match any of the pending options."
            )

        pending_action = state.pending_action
        pending_arguments = dict(state.context.get("pending_arguments", {}))
        self.conversation_state_repository.delete_state(chat_id)

        return PendingResolution(
            pending_action=pending_action,
            selected_option=PendingOption(
                option_id=selected["option_id"],
                display_name=selected["display_name"],
            ),
            pending_arguments=pending_arguments,
        )

    def clear_state(self, chat_id: int) -> bool:
        """Discard the pending state for a chat, if any.

        Args:
            chat_id: Telegram chat identifier to clear.

        Returns:
            ``True`` when a state was deleted, otherwise ``False``.

        Raises:
            SQLAlchemyError: If the delete or commit fails.
        """

        return self.conversation_state_repository.delete_state(chat_id)

    def _match_option_by_index(
        self, reply_text: str, options: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Match a free-form reply to a pending option using its 1-based index.

        Args:
            reply_text: Raw text sent by the vendor.
            options: Serialized pending options stored in the state context.

        Returns:
            The matching option payload, or ``None`` when no digit is found or
            the digit is out of range.
        """

        match = _OPTION_INDEX_PATTERN.search(reply_text)
        if match is None:
            return None

        index = int(match.group())
        if index < 1 or index > len(options):
            return None

        return options[index - 1]
