"""Service for generating collection summaries for customer follow-up."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from fiadobot.models.client import Client
from fiadobot.models.payment import Payment
from fiadobot.repositories.client_repository import ClientRepository
from fiadobot.repositories.payment_repository import PaymentRepository
from fiadobot.repositories.transaction_repository import TransactionRepository

from .balance_service import BalanceService
from .exceptions import CustomerNotFoundError
from .money import sum_money

# Collection summaries are a focused orchestration service.
# pylint: disable=too-few-public-methods


@dataclass(frozen=True, slots=True)
class CollectionSummaryLine:
    """Single sale line included in a collection summary."""

    product_id: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class CollectionSummaryTransaction:
    """Transaction entry included in a collection summary."""

    transaction_id: int
    date: datetime
    total_amount: Decimal
    status: str
    items: list[CollectionSummaryLine] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CollectionSummary:
    """Structured result for a customer's collection summary."""

    customer: Client
    transactions: list[CollectionSummaryTransaction] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)
    total_sales: Decimal = Decimal("0.00")
    total_payments: Decimal = Decimal("0.00")
    pending_balance: Decimal = Decimal("0.00")


class CollectionSummaryService:
    """Generate deterministic collection summaries for one customer."""

    def __init__(
        self,
        client_repository: ClientRepository,
        transaction_repository: TransactionRepository,
        payment_repository: PaymentRepository,
        balance_service: BalanceService,
    ) -> None:
        """Initialize the service with its repository dependencies."""

        self.client_repository = client_repository
        self.transaction_repository = transaction_repository
        self.payment_repository = payment_repository
        self.balance_service = balance_service

    def generate_collection_summary(self, customer_id: int) -> CollectionSummary:
        """Return a structured summary of sales and payments for a customer."""

        customer = self.client_repository.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} was not found.")

        transactions = self.transaction_repository.list_by_customer(customer_id)
        payments = self.payment_repository.list_by_customer(customer_id)

        summary_transactions = [
            CollectionSummaryTransaction(
                transaction_id=transaction.id,
                date=transaction.date,
                total_amount=transaction.total_amount,
                status=transaction.status,
                items=[
                    CollectionSummaryLine(
                        product_id=detail.product_id,
                        product_name=detail.product.name,
                        quantity=detail.quantity,
                        unit_price=detail.frozen_unit_price,
                        subtotal=detail.subtotal,
                    )
                    for detail in transaction.details
                ],
            )
            for transaction in transactions
        ]

        total_sales = sum_money(
            transaction.total_amount for transaction in transactions
        )
        total_payments = sum_money(payment.amount for payment in payments)
        pending_balance = self.balance_service.calculate_pending_balance(customer_id)
        return CollectionSummary(
            customer=customer,
            transactions=summary_transactions,
            payments=payments,
            total_sales=total_sales,
            total_payments=total_payments,
            pending_balance=pending_balance,
        )
