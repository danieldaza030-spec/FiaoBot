"""Authorized user repository for Telegram access control."""

from __future__ import annotations

from fiadobot.models.authorized_user import AuthorizedUser

from .base_repository import BaseRepository


class AuthorizedUserRepository(BaseRepository):
    """Repository for authorized Telegram chats.

    The repository centralizes manual access control entries for the bot.
    """

    def add_user(self, chat_id: int, role: str) -> AuthorizedUser:
        """Add or replace an authorized Telegram chat.

        Args:
            chat_id: Telegram chat identifier to authorize.
            role: Role assigned to the chat, such as vendor or tester.

        Returns:
            The persisted authorization record.

        Raises:
            SQLAlchemyError: If the insert or commit fails.
        """

        user = AuthorizedUser(chat_id=chat_id, role=role)
        merged_user = self.session.merge(user)
        self._commit()
        self.session.refresh(merged_user)
        return merged_user

    def get_by_chat_id(self, chat_id: int) -> AuthorizedUser | None:
        """Return an authorized chat by its identifier, if any.

        Args:
            chat_id: Telegram chat identifier to search.

        Returns:
            The matching authorization record or ``None`` when absent.
        """

        return self.session.get(AuthorizedUser, chat_id)

    def is_authorized(self, chat_id: int) -> bool:
        """Return whether a Telegram chat is authorized to use the bot.

        Args:
            chat_id: Telegram chat identifier to check.

        Returns:
            ``True`` when the chat is authorized, otherwise ``False``.
        """

        return self.get_by_chat_id(chat_id) is not None
