"""Transaction model mapped to the transacciones table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fiadobot.db.base import Base

# Declarative ORM models naturally expose attributes rather than methods.
# pylint: disable=too-few-public-methods

if TYPE_CHECKING:
    from .client import Client
    from .transaction_detail import TransactionDetail


class Transaction(Base):
    """Sale transaction registered for a customer.

    The transaction stores the frozen total amount and cancellation metadata,
    while its line items keep the historical unit prices used at sale time.

    Args:
        id: Internal identifier of the transaction.
        customer_id: Customer associated with the sale.
        date: Timestamp when the transaction was created.
        total_amount: Frozen total amount stored for the transaction.
        status: Current transaction status.
        cancellation_reason: Reason stored when the transaction is cancelled.
        cancelled_at: Timestamp when the transaction was cancelled.
    """

    __tablename__ = "transacciones"

    STATUS_ACTIVE = "activa"
    STATUS_CANCELLED = "anulada"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        "cliente_id",
        ForeignKey("clientes.id"),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(
        "fecha",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    total_amount: Mapped[Decimal] = mapped_column(
        "monto_total",
        Numeric(12, 2),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        "estado",
        String(20),
        nullable=False,
        server_default=text("'activa'"),
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        "motivo_anulacion",
        Text,
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        "anulada_en",
        DateTime(timezone=True),
        nullable=True,
    )

    customer: Mapped["Client"] = relationship(back_populates="transactions")
    details: Mapped[list["TransactionDetail"]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("estado IN ('activa', 'anulada')", name="status_valid"),
    )
