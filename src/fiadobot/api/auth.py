"""Access control helpers for validating Telegram chat authorization.

Every inbound Telegram message must be checked against the list of
authorized chats before any further processing happens (RF09, RNF02).
"""

from __future__ import annotations

from fiadobot.repositories.authorized_user_repository import AuthorizedUserRepository


def is_chat_authorized(
    chat_id: int,
    authorized_user_repository: AuthorizedUserRepository,
) -> bool:
    """Return whether a Telegram chat is authorized to use the bot.

    Args:
        chat_id: Telegram chat identifier to validate.
        authorized_user_repository: Repository used to check the allow list.

    Returns:
        ``True`` when the chat is authorized, otherwise ``False``.
    """

    return authorized_user_repository.is_authorized(chat_id)
