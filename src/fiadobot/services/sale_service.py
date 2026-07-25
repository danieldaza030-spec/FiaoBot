"""Service for registering customer sales in a deterministic way."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from fiadobot.models.transaction import Transaction
from fiadobot.repositories.client_repository import ClientRepository
from fiadobot.repositories.product_repository import ProductRepository
from fiadobot.repositories.transaction_repository import (
    TransactionCreateInput,
    TransactionDetailInput,
    TransactionRepository,
)

from .balance_service import BalanceService
from .exceptions import (
    CustomerNotFoundError,
    EmptySaleError,
    InvalidSaleItemError,
    ProductNotFoundError,
)
from .money import normalize_money

# Sale registration is a focused orchestration service.
# pylint: disable=too-few-public-methods


@dataclass(frozen=True, slots=True)
class SaleItemInput:
    """Input data for a single product line in a sale."""

    product_id: int
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class SaleItemResult:
    """Persisted sale line with pricing details."""

    product_id: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class SaleResult:
    """Result of a sale registration operation."""

    transaction: Transaction
    items: list[SaleItemResult] = field(default_factory=list)
    total_amount: Decimal = Decimal("0.00")
    pending_balance: Decimal = Decimal("0.00")


class SaleService:
    """Register customer sales and persist the resulting transaction."""

    def __init__(
        self,
        client_repository: ClientRepository,
        product_repository: ProductRepository,
        transaction_repository: TransactionRepository,
        balance_service: BalanceService,
    ) -> None:
        """Initialize the service with its repository dependencies."""

        self.client_repository = client_repository
        self.product_repository = product_repository
        self.transaction_repository = transaction_repository
        self.balance_service = balance_service

    def register_sale(
        self,
        customer_id: int,
        items: Sequence[SaleItemInput],
        *,
        date: datetime | None = None,
    ) -> SaleResult:
        """Register a sale from normalized item inputs."""

        customer = self.client_repository.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} was not found.")

        if not items:
            raise EmptySaleError("A sale must contain at least one item.")

        sale_items: list[SaleItemResult] = []
        transaction_details: list[TransactionDetailInput] = []

        for item in items:
            if item.quantity <= 0:
                raise InvalidSaleItemError("Item quantity must be greater than zero.")

            product = self.product_repository.get_by_id(item.product_id)
            if product is None:
                raise ProductNotFoundError(f"Product {item.product_id} was not found.")

            unit_price = normalize_money(product.current_price)
            subtotal = normalize_money(item.quantity * unit_price)
            sale_items.append(
                SaleItemResult(
                    product_id=product.id,
                    product_name=product.name,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )
            transaction_details.append(
                TransactionDetailInput(
                    product_id=product.id,
                    quantity=item.quantity,
                    frozen_unit_price=unit_price,
                    subtotal=subtotal,
                )
            )

        total_amount = normalize_money(sum(item.subtotal for item in sale_items))
        transaction = self.transaction_repository.create_transaction(
            TransactionCreateInput(
                customer_id=customer_id,
                total_amount=total_amount,
                details=transaction_details,
                date=date,
            )
        )
        pending_balance = self.balance_service.calculate_pending_balance(customer_id)

        return SaleResult(
            transaction=transaction,
            items=sale_items,
            total_amount=total_amount,
            pending_balance=pending_balance,
        )
