"""Conversation state repository for pending Telegram interactions."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from fiadobot.models.conversation_state import ConversationState

from .base_repository import BaseRepository


class ConversationStateRepository(BaseRepository):
    """Repository for pending conversation states."""

    def get_by_chat_id(self, chat_id: int) -> ConversationState | None:
        """Return the pending state for a chat, if any."""

        return self.session.get(ConversationState, chat_id)

    def upsert_state(
        self,
        chat_id: int,
        pending_action: str,
        context: dict[str, Any],
    ) -> ConversationState:
        """Create or replace the pending state for a chat."""

        state = ConversationState(
            chat_id=chat_id,
            pending_action=pending_action,
            context=context,
        )
        merged_state = self.session.merge(state)
        self._commit()
        self.session.refresh(merged_state)
        return merged_state

    def delete_state(self, chat_id: int) -> bool:
        """Delete the pending state for a chat if it exists."""

        state = self.get_by_chat_id(chat_id)
        if state is None:
            return False

        self.session.delete(state)
        self._commit()
        return True

    def list_pending(self) -> list[ConversationState]:
        """Return all pending conversation states."""

        statement = select(ConversationState).order_by(
            ConversationState.created_at.asc()
        )
        return list(self.session.scalars(statement).all())
