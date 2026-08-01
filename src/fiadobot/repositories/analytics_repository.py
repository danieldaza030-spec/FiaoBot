"""Read-only repository for historical analytics queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import desc, func, select

from fiadobot.models.client import Client
from fiadobot.models.product import Product
from fiadobot.models.transaction import Transaction
from fiadobot.models.transaction_detail import TransactionDetail

from .base_repository import BaseRepository


@dataclass(frozen=True, slots=True)
class ProductSalesRow:
    """Aggregated sales row grouped by product.

    Args:
        product_id: Identifier of the product.
        product_name: Stored product name.
        units_sold: Total sold quantity in the selected range.
        transaction_count: Number of transactions that included the product.
        total_amount: Frozen sales amount aggregated for the product.
    """

    product_id: int
    product_name: str
    units_sold: Decimal
    transaction_count: int
    total_amount: Decimal


@dataclass(frozen=True, slots=True)
class FrequentCustomerRow:
    """Aggregated activity row grouped by customer.

    Args:
        customer_id: Identifier of the customer.
        customer_name: Stored customer name.
        transaction_count: Number of transactions in the selected range.
        total_amount: Frozen sales amount aggregated for the customer.
    """

    customer_id: int
    customer_name: str
    transaction_count: int
    total_amount: Decimal


class AnalyticsRepository(BaseRepository):
    """Repository for read-only analytics aggregation queries."""

    def list_sales_by_product(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[ProductSalesRow]:
        """Return aggregated sales grouped by product.

        Args:
            start_date: Inclusive lower bound for the analytics range.
            end_date: Inclusive upper bound for the analytics range.

        Returns:
            Sales rows ordered by total sales amount and product name.
        """

        # SQLAlchemy aggregate expressions are not plain Python callables.
        # pylint: disable=assignment-from-no-return,not-callable
        total_units = func.coalesce(func.sum(TransactionDetail.quantity), 0)
        transaction_count = func.count(func.distinct(Transaction.id))
        total_amount = func.coalesce(func.sum(TransactionDetail.subtotal), 0)
        statement = (
            select(
                Product.id,
                Product.name,
                total_units.label("units_sold"),
                transaction_count.label("transaction_count"),
                total_amount.label("total_amount"),
            )
            .join(TransactionDetail, TransactionDetail.product_id == Product.id)
            .join(Transaction, Transaction.id == TransactionDetail.transaction_id)
            .where(
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.status != Transaction.STATUS_CANCELLED,
            )
            .group_by(Product.id, Product.name)
            .order_by(desc(total_amount), Product.name.asc())
        )

        rows = self.session.execute(statement).all()
        # pylint: enable=assignment-from-no-return,not-callable
        return [
            ProductSalesRow(
                product_id=int(product_id),
                product_name=str(product_name),
                units_sold=Decimal(str(units_sold)),
                transaction_count=int(transaction_count_value),
                total_amount=Decimal(str(total_amount_value)),
            )
            for (
                product_id,
                product_name,
                units_sold,
                transaction_count_value,
                total_amount_value,
            ) in rows
        ]

    def list_frequent_customers(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[FrequentCustomerRow]:
        """Return aggregated sales grouped by customer.

        Args:
            start_date: Inclusive lower bound for the analytics range.
            end_date: Inclusive upper bound for the analytics range.

        Returns:
            Customer rows ordered by transaction count and total amount.
        """

        # SQLAlchemy aggregate expressions are not plain Python callables.
        # pylint: disable=assignment-from-no-return,not-callable
        transaction_count = func.count(Transaction.id)
        total_amount = func.coalesce(func.sum(Transaction.total_amount), 0)
        statement = (
            select(
                Client.id,
                Client.name,
                transaction_count.label("transaction_count"),
                total_amount.label("total_amount"),
            )
            .join(Transaction, Transaction.customer_id == Client.id)
            .where(
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.status != Transaction.STATUS_CANCELLED,
            )
            .group_by(Client.id, Client.name)
            .order_by(desc(transaction_count), desc(total_amount), Client.name.asc())
        )

        rows = self.session.execute(statement).all()
        # pylint: enable=assignment-from-no-return,not-callable
        return [
            FrequentCustomerRow(
                customer_id=int(customer_id),
                customer_name=str(customer_name),
                transaction_count=int(transaction_count_value),
                total_amount=Decimal(str(total_amount_value)),
            )
            for (
                customer_id,
                customer_name,
                transaction_count_value,
                total_amount_value,
            ) in rows
        ]
