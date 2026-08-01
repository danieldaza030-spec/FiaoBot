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
    """Input data required to persist a transaction detail.

    Args:
        product_id: Identifier of the product included in the line.
        quantity: Quantity sold for the product.
        frozen_unit_price: Unit price stored at sale time.
        subtotal: Precomputed subtotal for the line.
    """

    product_id: int
    quantity: Decimal
    frozen_unit_price: Decimal
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class TransactionCreateInput:
    """Input data required to persist a transaction aggregate.

    Args:
        customer_id: Identifier of the customer receiving the sale.
        total_amount: Precomputed total amount for the transaction.
        details: Line items to persist under the transaction.
        date: Optional timestamp to assign to the transaction.
    """

    customer_id: int
    total_amount: Decimal
    details: Sequence[TransactionDetailInput] = field(default_factory=tuple)
    date: datetime | None = None


class TransactionRepository(BaseRepository):
    """Repository for transaction data access operations.

    The repository owns transaction persistence, listing and cancellation.
    """

    def create_transaction(self, data: TransactionCreateInput) -> Transaction:
        """Persist a transaction and its details as a single database unit.

        Args:
            data: Transaction header and line items to persist.

        Returns:
            The persisted transaction header.

        Raises:
            SQLAlchemyError: If the insert or commit fails.
        """

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
        """Return a transaction by primary key, if it exists.

        Args:
            transaction_id: Primary key of the transaction to load.

        Returns:
            The matching transaction or ``None`` when no record exists.
        """

        return self.session.get(Transaction, transaction_id)

    def list_by_customer(
        self,
        customer_id: int,
        *,
        include_cancelled: bool = False,
    ) -> list[Transaction]:
        """Return transactions for a customer ordered from newest to oldest.

        Args:
            customer_id: Primary key of the customer whose transactions are needed.
            include_cancelled: Whether cancelled transactions should be included.

        Returns:
            Customer transactions ordered from newest to oldest.

        Raises:
            SQLAlchemyError: If the query fails.
        """

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
        """Return transactions within a date range ordered from newest to oldest.

        Args:
            start_date: Inclusive lower bound for the query.
            end_date: Inclusive upper bound for the query.
            include_cancelled: Whether cancelled transactions should be included.

        Returns:
            Transactions that fall within the requested date range.

        Raises:
            SQLAlchemyError: If the query fails.
        """

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
        """Mark a transaction as cancelled without deleting it.

        Args:
            transaction_id: Primary key of the transaction to cancel.
            reason: Human-readable cancellation reason.
            cancelled_at: Optional timestamp to assign to the cancellation.

        Returns:
            The cancelled transaction or ``None`` when it does not exist.

        Raises:
            SQLAlchemyError: If the update or commit fails.
        """

        transaction = self.get_by_id(transaction_id)
        if transaction is None:
            return None

        transaction.status = Transaction.STATUS_CANCELLED
        transaction.cancellation_reason = reason
        transaction.cancelled_at = cancelled_at or datetime.now(tz=timezone.utc)
        self._commit()
        self.session.refresh(transaction)
        return transaction
