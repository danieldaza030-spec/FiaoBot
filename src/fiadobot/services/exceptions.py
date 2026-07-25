"""Exception hierarchy for fiadobot business services."""

from __future__ import annotations

# Service exceptions are simple markers and intentionally lightweight.
# pylint: disable=too-few-public-methods


class ServiceError(Exception):
    """Base class for all service-layer errors."""


class EntityNotFoundError(ServiceError):
    """Base class for missing entity errors."""


class CustomerNotFoundError(EntityNotFoundError):
    """Raised when a customer cannot be found."""


class ProductNotFoundError(EntityNotFoundError):
    """Raised when a product cannot be found."""


class TransactionNotFoundError(EntityNotFoundError):
    """Raised when a transaction cannot be found."""


class EmptySaleError(ServiceError):
    """Raised when a sale is created without items."""


class InvalidSaleItemError(ServiceError):
    """Raised when a sale item has invalid quantity or price data."""


class InvalidPaymentAmountError(ServiceError):
    """Raised when a payment amount is invalid."""


class InvalidCancellationReasonError(ServiceError):
    """Raised when a cancellation reason is missing or blank."""


class InvalidPriceError(ServiceError):
    """Raised when a product price is invalid."""


class TransactionAlreadyCancelledError(ServiceError):
    """Raised when a transaction is cancelled more than once."""
