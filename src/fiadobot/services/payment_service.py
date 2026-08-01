"""Service for registering customer payments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fiadobot.models.payment import Payment
from fiadobot.repositories.client_repository import ClientRepository
from fiadobot.repositories.payment_repository import PaymentRepository

from .balance_service import BalanceService
from .exceptions import CustomerNotFoundError, InvalidPaymentAmountError
from .money import normalize_money

# Payment registration is a focused orchestration service.
# pylint: disable=too-few-public-methods


@dataclass(frozen=True, slots=True)
class PaymentResult:
    """Structured result returned after registering a payment.

    Args:
        payment: Persisted payment record.
        pending_balance: Updated pending balance after applying the payment.
    """

    payment: Payment
    pending_balance: Decimal = Decimal("0.00")


class PaymentService:
    """Register customer payments and recompute the outstanding balance.

    Args:
        client_repository: Repository used to validate that the customer exists.
        payment_repository: Repository used to persist payments.
        balance_service: Service used to recalculate the pending balance.
    """

    def __init__(
        self,
        client_repository: ClientRepository,
        payment_repository: PaymentRepository,
        balance_service: BalanceService,
    ) -> None:
        """Initialize the service with its repository dependencies.

        Args:
            client_repository: Repository used to validate customers.
            payment_repository: Repository used to store payments.
            balance_service: Service used to recalculate balances.

        Returns:
            None.

        Raises:
            None.
        """

        self.client_repository = client_repository
        self.payment_repository = payment_repository
        self.balance_service = balance_service

    def register_payment(
        self,
        customer_id: int,
        amount: Decimal,
        *,
        date: datetime | None = None,
    ) -> PaymentResult:
        """Register a payment and return the updated balance.

        Args:
            customer_id: Identifier of the customer making the payment.
            amount: Amount paid by the customer.
            date: Optional timestamp to assign to the payment.

        Returns:
            The persisted payment together with the updated pending balance.

        Raises:
            CustomerNotFoundError: If the customer does not exist.
            InvalidPaymentAmountError: If the amount is zero or negative.
        """

        customer = self.client_repository.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} was not found.")

        if amount <= 0:
            raise InvalidPaymentAmountError("Payment amount must be greater than zero.")

        payment = self.payment_repository.create_payment(
            customer_id=customer_id,
            amount=normalize_money(amount),
            date=date,
        )
        pending_balance = self.balance_service.calculate_pending_balance(customer_id)
        return PaymentResult(payment=payment, pending_balance=pending_balance)
