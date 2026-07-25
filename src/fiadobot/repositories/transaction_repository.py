"""Transaction repository with persistence, querying, and cancellation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select

from fiadobot.models.transaction import Transaction
from fiadobot.models.transaction_detail import TransactionDetail

from .base_repository import BaseRepository


@dataclass(frozen=True, slots=True)
class TransactionDetailInput:
    """Input data required to persist a transaction detail."""

    product_id: int
    quantity: Decimal
    frozen_unit_price: Decimal
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class TransactionCreateInput:
    """Input data required to persist a transaction aggregate."""

    customer_id: int
    total_amount: Decimal
    details: Sequence[TransactionDetailInput] = field(default_factory=tuple)
    date: datetime | None = None


class TransactionRepository(BaseRepository):
    """Repository for transaction data access operations."""

    def create_transaction(self, data: TransactionCreateInput) -> Transaction:
        """Persist a transaction and its details as a single database unit."""

        transaction = Transaction(
            customer_id=data.customer_id,
            total_amount=data.total_amount,
        )
        if data.date is not None:
            transaction.date = data.date

        self.session.add(transaction)
        self.session.flush()

        for detail_data in data.details:
            detail = TransactionDetail(
                transaction_id=transaction.id,
                product_id=detail_data.product_id,
                quantity=detail_data.quantity,
                frozen_unit_price=detail_data.frozen_unit_price,
                subtotal=detail_data.subtotal,
            )
            self.session.add(detail)

        self._commit()
        self.session.refresh(transaction)
        return transaction

    def get_by_id(self, transaction_id: int) -> Transaction | None:
        """Return a transaction by primary key, if it exists."""

        return self.session.get(Transaction, transaction_id)

    def list_by_customer(
        self,
        customer_id: int,
        *,
        include_cancelled: bool = False,
    ) -> list[Transaction]:
        """Return transactions for a customer ordered from newest to oldest."""

        statement = select(Transaction).where(Transaction.customer_id == customer_id)
        if not include_cancelled:
            statement = statement.where(
                Transaction.status != Transaction.STATUS_CANCELLED
            )

        statement = statement.order_by(Transaction.date.desc(), Transaction.id.desc())
        return list(self.session.scalars(statement).all())

    def list_between_dates(
        self,
        start_date: datetime,
        end_date: datetime,
        *,
        include_cancelled: bool = False,
    ) -> list[Transaction]:
        """Return transactions within a date range ordered from newest to oldest."""

        statement = select(Transaction).where(
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        if not include_cancelled:
            statement = statement.where(
                Transaction.status != Transaction.STATUS_CANCELLED
            )

        statement = statement.order_by(Transaction.date.desc(), Transaction.id.desc())
        return list(self.session.scalars(statement).all())

    def cancel_transaction(
        self,
        transaction_id: int,
        reason: str,
        *,
        cancelled_at: datetime | None = None,
    ) -> Transaction | None:
        """Mark a transaction as cancelled without deleting it."""

        transaction = self.get_by_id(transaction_id)
        if transaction is None:
            return None

        transaction.status = Transaction.STATUS_CANCELLED
        transaction.cancellation_reason = reason
        transaction.cancelled_at = cancelled_at or datetime.now(tz=timezone.utc)
        self._commit()
        self.session.refresh(transaction)
        return transaction
