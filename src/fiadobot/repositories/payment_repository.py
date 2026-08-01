"""Payment repository for customer payment persistence and queries."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from fiadobot.models.payment import Payment

from .base_repository import BaseRepository


class PaymentRepository(BaseRepository):
    """Repository for payment data access operations.

    The repository owns persistence and queries for payment records.
    """

    def create_payment(
        self,
        customer_id: int,
        amount: Decimal,
        *,
        date: datetime | None = None,
    ) -> Payment:
        """Create a payment and persist it to the database.

        Args:
            customer_id: Identifier of the customer making the payment.
            amount: Payment amount to persist.
            date: Optional timestamp to assign to the payment.

        Returns:
            The persisted payment record.

        Raises:
            SQLAlchemyError: If the insert or commit fails.
        """

        payment = Payment(customer_id=customer_id, amount=amount)
        if date is not None:
            payment.date = date

        self.session.add(payment)
        self._commit()
        self.session.refresh(payment)
        return payment

    def get_by_id(self, payment_id: int) -> Payment | None:
        """Return a payment by primary key, if it exists.

        Args:
            payment_id: Primary key of the payment to load.

        Returns:
            The matching payment or ``None`` when no record exists.
        """

        return self.session.get(Payment, payment_id)

    def list_by_customer(self, customer_id: int) -> list[Payment]:
        """Return all payments recorded for a customer.

        Args:
            customer_id: Primary key of the customer whose payments are needed.

        Returns:
            Payments ordered from oldest to newest.
        """

        statement = select(Payment).where(
            Payment.customer_id == customer_id
        ).order_by(Payment.date.asc())
        return list(self.session.scalars(statement).all())
