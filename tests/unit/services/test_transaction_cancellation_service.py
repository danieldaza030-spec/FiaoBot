"""Unit tests for the transaction cancellation service."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fiadobot.models.transaction import Transaction
from fiadobot.services.balance_service import BalanceService
from fiadobot.services.exceptions import (
    InvalidCancellationReasonError,
    TransactionAlreadyCancelledError,
    TransactionNotFoundError,
)
from fiadobot.services.transaction_cancellation_service import (
    TransactionCancellationService,
)


def test_cancel_transaction_trims_reason_and_updates_balance() -> None:
    """It should cancel an active transaction and recompute the balance."""

    transaction = SimpleNamespace(
        id=10,
        customer_id=7,
        status=Transaction.STATUS_ACTIVE,
    )
    transaction_repository = MagicMock()
    transaction_repository.get_by_id.return_value = transaction
    transaction_repository.cancel_transaction.return_value = SimpleNamespace(
        id=10,
        customer_id=7,
        status=Transaction.STATUS_CANCELLED,
    )

    balance_service = MagicMock(spec=BalanceService)
    balance_service.calculate_pending_balance.return_value = Decimal("40.00")

    service = TransactionCancellationService(
        transaction_repository,
        balance_service,
    )

    result = service.cancel_transaction(10, "  motivo de prueba  ")

    assert result.transaction.id == 10
    assert result.pending_balance == Decimal("40.00")
    transaction_repository.cancel_transaction.assert_called_once_with(
        transaction_id=10,
        reason="motivo de prueba",
        cancelled_at=None,
    )
    balance_service.calculate_pending_balance.assert_called_once_with(7)


def test_cancel_transaction_raises_when_reason_is_blank() -> None:
    """It should reject blank cancellation reasons."""

    service = TransactionCancellationService(MagicMock(), MagicMock())

    with pytest.raises(InvalidCancellationReasonError):
        service.cancel_transaction(10, "   ")


def test_cancel_transaction_raises_when_transaction_missing() -> None:
    """It should raise when the transaction id does not exist."""

    transaction_repository = MagicMock()
    transaction_repository.get_by_id.return_value = None
    service = TransactionCancellationService(transaction_repository, MagicMock())

    with pytest.raises(TransactionNotFoundError):
        service.cancel_transaction(10, "motivo")


def test_cancel_transaction_raises_when_transaction_already_cancelled() -> None:
    """It should reject cancelling a transaction twice."""

    transaction_repository = MagicMock()
    transaction_repository.get_by_id.return_value = SimpleNamespace(
        id=10,
        customer_id=7,
        status=Transaction.STATUS_CANCELLED,
    )
    service = TransactionCancellationService(transaction_repository, MagicMock())

    with pytest.raises(TransactionAlreadyCancelledError):
        service.cancel_transaction(10, "motivo")
