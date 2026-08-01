"""Authorized user model mapped to the usuarios_autorizados table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from fiadobot.db.base import Base

# Declarative ORM models naturally expose attributes rather than methods.
# pylint: disable=too-few-public-methods


class AuthorizedUser(Base):
    """Telegram chat authorized to interact with the bot.

    The table acts as a small access-control list for the Telegram backend.

    Args:
        chat_id: Telegram chat identifier allowed to use the bot.
        role: Access role assigned to the chat.
        added_at: Timestamp when the authorization was created.
    """

    __tablename__ = "usuarios_autorizados"

    ROLE_VENDOR = "vendedor"
    ROLE_TESTER = "tester"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column("rol", String(20), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        "agregado_en",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        CheckConstraint("rol IN ('vendedor', 'tester')", name="role_valid"),
    )
