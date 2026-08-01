"""Service for calculating customer pending balances."""

from __future__ import annotations

from decimal import Decimal

from fiadobot.repositories.client_repository import ClientRepository
from fiadobot.repositories.payment_repository import PaymentRepository
from fiadobot.repositories.transaction_repository import TransactionRepository

from .exceptions import CustomerNotFoundError
from .money import normalize_money, sum_money

# Balance calculation is a single focused operation.
# pylint: disable=too-few-public-methods


class BalanceService:
    """Calculate pending customer balances from the accounting data.

    Args:
        client_repository: Repository used to validate that the customer exists.
        transaction_repository: Repository used to read active transactions.
        payment_repository: Repository used to read registered payments.
    """

    def __init__(
        self,
        client_repository: ClientRepository,
        transaction_repository: TransactionRepository,
        payment_repository: PaymentRepository,
    ) -> None:
        """Initialize the service with its repository dependencies.

        Args:
            client_repository: Repository used to validate customers.
            transaction_repository: Repository used to query sales.
            payment_repository: Repository used to query payments.

        Returns:
            None.

        Raises:
            None.
        """

        self.client_repository = client_repository
        self.transaction_repository = transaction_repository
        self.payment_repository = payment_repository

    def calculate_pending_balance(self, customer_id: int) -> Decimal:
        """Return the current pending balance for a customer.

        Args:
            customer_id: Identifier of the customer whose balance is required.

        Returns:
            The pending balance after subtracting all payments from the active
            transaction totals.

        Raises:
            CustomerNotFoundError: If the customer does not exist.
        """

        customer = self.client_repository.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} was not found.")

        active_transactions = self.transaction_repository.list_by_customer(customer_id)
        payments = self.payment_repository.list_by_customer(customer_id)

        total_sales = sum_money(
            transaction.total_amount for transaction in active_transactions
        )
        total_payments = sum_money(payment.amount for payment in payments)
        return normalize_money(total_sales - total_payments)
