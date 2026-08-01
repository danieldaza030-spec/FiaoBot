"""Customer model mapped to the clientes table."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fiadobot.db.base import Base

# Declarative ORM models naturally expose attributes rather than methods.
# pylint: disable=too-few-public-methods

if TYPE_CHECKING:
    from .payment import Payment
    from .transaction import Transaction


class Client(Base):
    """Customer registered in the system.

    This model stores the customer identity used across sales, payments and
    fuzzy name matching.

    Args:
        id: Internal identifier of the customer.
        name: Unique customer name stored in the database.
        alias: Optional nickname or short name.
        phone_number: Optional contact phone number.
        created_at: Timestamp when the customer was created.
    """

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        "nombre",
        String(150),
        unique=True,
        nullable=False,
    )
    alias: Mapped[str | None] = mapped_column("alias", String(150), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(
        "telefono",
        String(30),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        "creado_en",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer",
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="customer")
