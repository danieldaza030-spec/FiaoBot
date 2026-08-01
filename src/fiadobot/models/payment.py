"""Payment model mapped to the pagos table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fiadobot.db.base import Base

# Declarative ORM models naturally expose attributes rather than methods.
# pylint: disable=too-few-public-methods

if TYPE_CHECKING:
    from .client import Client


class Payment(Base):
    """Registered payment made by a customer.

    The model stores the amount paid and the timestamp used in balance
    calculations.

    Args:
        id: Internal identifier of the payment.
        customer_id: Customer that made the payment.
        amount: Amount recorded for the payment.
        date: Timestamp when the payment was created.
    """

    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        "cliente_id",
        ForeignKey("clientes.id"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column("monto", Numeric(12, 2), nullable=False)
    date: Mapped[datetime] = mapped_column(
        "fecha",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    customer: Mapped["Client"] = relationship(back_populates="payments")
