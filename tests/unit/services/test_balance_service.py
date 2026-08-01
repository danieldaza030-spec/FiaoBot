"""Unit tests for the customer balance service."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fiadobot.services.balance_service import BalanceService
from fiadobot.services.exceptions import CustomerNotFoundError


def test_calculate_pending_balance_subtracts_payments_and_excludes_cancelled() -> None:
    """It should compute the pending balance from active sales and payments."""

    client_repository = MagicMock()
    client_repository.get_by_id.return_value = SimpleNamespace(id=1)

    transaction_repository = MagicMock()
    transaction_repository.list_by_customer.return_value = [
        SimpleNamespace(total_amount=Decimal("120.00")),
        SimpleNamespace(total_amount=Decimal("80.25")),
    ]

    payment_repository = MagicMock()
    payment_repository.list_by_customer.return_value = [
        SimpleNamespace(amount=Decimal("50.10")),
        SimpleNamespace(amount=Decimal("10.15")),
    ]

    service = BalanceService(
        client_repository,
        transaction_repository,
        payment_repository,
    )

    pending_balance = service.calculate_pending_balance(1)

    assert pending_balance == Decimal("140.00")
    client_repository.get_by_id.assert_called_once_with(1)
    transaction_repository.list_by_customer.assert_called_once_with(1)
    payment_repository.list_by_customer.assert_called_once_with(1)


def test_calculate_pending_balance_raises_when_customer_missing() -> None:
    """It should raise a domain error if the customer does not exist."""

    client_repository = MagicMock()
    client_repository.get_by_id.return_value = None

    service = BalanceService(
        client_repository,
        MagicMock(),
        MagicMock(),
    )

    with pytest.raises(CustomerNotFoundError):
        service.calculate_pending_balance(99)
