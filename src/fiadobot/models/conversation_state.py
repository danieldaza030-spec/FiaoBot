"""Conversation state model mapped to the estado_conversacion table."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fiadobot.db.base import Base

# Declarative ORM models naturally expose attributes rather than methods.
# pylint: disable=too-few-public-methods


class ConversationState(Base):
    """Pending conversation state for a Telegram chat.

    The model stores transient data required to resume a disambiguation flow
    or any other pending conversational branch.

    Args:
        chat_id: Telegram chat identifier that owns the state.
        pending_action: Action waiting for a user response.
        context: Serialized data required to resume the conversation.
        created_at: Timestamp when the state was created.
    """

    __tablename__ = "estado_conversacion"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pending_action: Mapped[str] = mapped_column(
        "accion_pendiente",
        String(50),
        nullable=False,
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        "contexto",
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        "creado_en",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
