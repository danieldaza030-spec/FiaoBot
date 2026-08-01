"""Transaction detail model mapped to the transaccion_detalle table."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fiadobot.db.base import Base

# Declarative ORM models naturally expose attributes rather than methods.
# pylint: disable=too-few-public-methods

if TYPE_CHECKING:
    from .product import Product
    from .transaction import Transaction


class TransactionDetail(Base):
    """A single line item inside a sale transaction.

    Each row stores the frozen unit price and subtotal used when the sale was
    created so historical balances remain stable over time.

    Args:
        id: Internal identifier of the line item.
        transaction_id: Transaction that owns the line item.
        product_id: Product referenced by the line item.
        quantity: Quantity sold for the line item.
        frozen_unit_price: Unit price stored when the sale was created.
        subtotal: Frozen subtotal for the line item.
    """

    __tablename__ = "transaccion_detalle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        "transaccion_id",
        ForeignKey("transacciones.id"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        "producto_id",
        ForeignKey("productos.id"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(
        "cantidad",
        Numeric(10, 2),
        nullable=False,
    )
    frozen_unit_price: Mapped[Decimal] = mapped_column(
        "precio_unitario_congelado",
        Numeric(12, 2),
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        "subtotal",
        Numeric(12, 2),
        nullable=False,
    )

    transaction: Mapped["Transaction"] = relationship(back_populates="details")
    product: Mapped["Product"] = relationship(back_populates="details")

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="quantity_positive"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
    )
