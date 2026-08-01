"""Exception hierarchy for fiadobot business services."""

from __future__ import annotations

# Service exceptions are simple markers and intentionally lightweight.
# pylint: disable=too-few-public-methods


class ServiceError(Exception):
    """Base class for all service-layer errors.

    All business exceptions inherit from this type so callers can catch a
    single domain-specific failure category when needed.
    """


class EntityNotFoundError(ServiceError):
    """Base class for missing entity errors.

    This marker class groups not-found errors for repository-backed entities.
    """


class CustomerNotFoundError(EntityNotFoundError):
    """Raised when a customer cannot be found.

    The error is used when a customer identifier does not resolve to a stored
    record.
    """


class ProductNotFoundError(EntityNotFoundError):
    """Raised when a product cannot be found.

    The error is used when a product identifier or name cannot be resolved.
    """


class TransactionNotFoundError(EntityNotFoundError):
    """Raised when a transaction cannot be found.

    The error is used when a transaction identifier does not exist.
    """


class EmptySaleError(ServiceError):
    """Raised when a sale is created without items.

    The service rejects empty sales because they do not produce a valid
    accounting entry.
    """


class InvalidSaleItemError(ServiceError):
    """Raised when a sale item has invalid quantity or price data.

    The error covers malformed sale lines such as zero or negative quantities.
    """


class InvalidPaymentAmountError(ServiceError):
    """Raised when a payment amount is invalid.

    The error is used when a payment amount is zero or negative.
    """


class InvalidCancellationReasonError(ServiceError):
    """Raised when a cancellation reason is missing or blank.

    The cancellation flow requires a human-readable explanation for auditing.
    """


class InvalidPriceError(ServiceError):
    """Raised when a product price is invalid.

    The error is used when a product price is zero or negative.
    """


class TransactionAlreadyCancelledError(ServiceError):
    """Raised when a transaction is cancelled more than once.

    The service prevents repeated cancellations so transaction history remains
    consistent.
    """


class NoPendingStateError(ServiceError):
    """Raised when a chat has no pending conversational state.

    The error is used when the caller tries to resolve or clear a pending
    flow for a chat that has none.
    """


class DisambiguationOptionsError(ServiceError):
    """Raised when a disambiguation flow is started with too few options.

    Disambiguation only makes sense when there are at least two candidates
    for the vendor to choose from.
    """


class PendingActionNameTooLongError(ServiceError):
    """Raised when a pending action name exceeds the stored column size.

    The `estado_conversacion.accion_pendiente` column has a fixed maximum
    length, so this is validated before attempting to persist the state.
    """


class PendingReplyNotResolvedError(ServiceError):
    """Raised when a vendor reply cannot be matched to a pending option.

    The pending state is intentionally kept untouched so the backend can ask
    the vendor to reply again without losing the original context.
    """
