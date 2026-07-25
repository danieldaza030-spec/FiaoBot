"""Service for cancelling transactions without deleting them."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fiadobot.models.transaction import Transaction
from fiadobot.repositories.transaction_repository import TransactionRepository

from .balance_service import BalanceService
from .exceptions import (
    InvalidCancellationReasonError,
    TransactionAlreadyCancelledError,
    TransactionNotFoundError,
)

# Transaction cancellation is a focused orchestration service.
# pylint: disable=too-few-public-methods


@dataclass(frozen=True, slots=True)
class CancellationResult:
    """Result of a transaction cancellation operation."""

    transaction: Transaction
    pending_balance: Decimal


class TransactionCancellationService:
    """Cancel transactions and return the updated customer balance."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        balance_service: BalanceService,
    ) -> None:
        """Initialize the service with its repository dependencies."""

        self.transaction_repository = transaction_repository
        self.balance_service = balance_service

    def cancel_transaction(
        self,
        transaction_id: int,
        reason: str,
        *,
        cancelled_at: datetime | None = None,
    ) -> CancellationResult:
        """Cancel a transaction and return the updated pending balance."""

        if not reason.strip():
            raise InvalidCancellationReasonError(
                "Cancellation reason cannot be blank."
            )

        transaction = self.transaction_repository.get_by_id(transaction_id)
        if transaction is None:
            raise TransactionNotFoundError(
                f"Transaction {transaction_id} was not found."
            )

        if transaction.status == Transaction.STATUS_CANCELLED:
            raise TransactionAlreadyCancelledError(
                f"Transaction {transaction_id} is already cancelled."
            )

        cancelled_transaction = self.transaction_repository.cancel_transaction(
            transaction_id=transaction_id,
            reason=reason.strip(),
            cancelled_at=cancelled_at,
        )
        if cancelled_transaction is None:
            raise TransactionNotFoundError(
                f"Transaction {transaction_id} was not found."
            )

        pending_balance = self.balance_service.calculate_pending_balance(
            cancelled_transaction.customer_id
        )
        return CancellationResult(
            transaction=cancelled_transaction,
            pending_balance=pending_balance,
        )
