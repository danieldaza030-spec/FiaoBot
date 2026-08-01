"""Minimal Telegram update payloads consumed by the webhook endpoint.

Only the fields required to route a text message are modeled here; unknown
fields sent by Telegram are ignored by default (Pydantic v2 behavior).
"""

from __future__ import annotations

from pydantic import BaseModel


class TelegramChat(BaseModel):
    """Telegram chat identifier payload.

    Args:
        id: Telegram chat identifier.
    """

    id: int


class TelegramMessage(BaseModel):
    """Minimal Telegram message payload.

    Args:
        chat: Chat the message belongs to.
        text: Text content of the message, if any.
    """

    chat: TelegramChat
    text: str | None = None


class TelegramUpdate(BaseModel):
    """Minimal Telegram update payload.

    Args:
        update_id: Unique identifier assigned by Telegram to this update.
        message: Incoming message payload, if the update contains one.
    """

    update_id: int
    message: TelegramMessage | None = None
