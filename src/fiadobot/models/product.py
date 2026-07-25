"""Product model mapped to the productos table."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fiadobot.db.base import Base

# Declarative ORM models naturally expose attributes rather than methods.
# pylint: disable=too-few-public-methods

if TYPE_CHECKING:
    from .transaction_detail import TransactionDetail


class Product(Base):
    """Product available for sale."""

    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        "nombre",
        String(100),
        unique=True,
        nullable=False,
    )
    current_price: Mapped[Decimal] = mapped_column(
        "precio_actual",
        Numeric(12, 2),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        "activo",
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )

    details: Mapped[list["TransactionDetail"]] = relationship(back_populates="product")
