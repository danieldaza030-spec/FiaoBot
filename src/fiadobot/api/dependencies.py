"""FastAPI dependency providers wiring repositories, services and adapters.

This module is the composition root for the Telegram integration: it is the
only place that knows how to build repositories, services, the prompt
builder and the LLM provider from application configuration. Everything
downstream (the orchestrator) only receives already-built collaborators.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from fiadobot.config import AppConfig, load_config
from fiadobot.db.session import create_session_factory
from fiadobot.llm.factory import create_llm_provider
from fiadobot.llm.provider import LLMProvider
from fiadobot.prompting.prompt_builder import PromptBuilder
from fiadobot.repositories import (
    AnalyticsRepository,
    AuthorizedUserRepository,
    ClientRepository,
    ConversationStateRepository,
    PaymentRepository,
    ProductRepository,
    TransactionRepository,
)
from fiadobot.services import (
    AnalyticsService,
    BalanceService,
    CollectionSummaryService,
    ConversationStateService,
    PaymentService,
    ProductPriceService,
    SaleService,
    TransactionCancellationService,
)

from .telegram_client import TelegramClient


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return the cached application configuration.

    Returns:
        The application configuration loaded from environment variables.
    """

    return load_config()


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return a cached SQLAlchemy session factory bound to the configured DB.

    Returns:
        The session factory used to open request-scoped sessions.
    """

    return create_session_factory()


def get_db_session() -> Iterator[Session]:
    """Yield a database session scoped to a single request.

    Returns:
        An iterator yielding the request-scoped SQLAlchemy session.
    """

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_client_repository(
    session: Session = Depends(get_db_session),
) -> ClientRepository:
    """Provide a customer repository bound to the request session.

    Args:
        session: Request-scoped SQLAlchemy session.

    Returns:
        A customer repository bound to the request session.
    """

    return ClientRepository(session)


def get_product_repository(
    session: Session = Depends(get_db_session),
) -> ProductRepository:
    """Provide a product repository bound to the request session.

    Args:
        session: Request-scoped SQLAlchemy session.

    Returns:
        A product repository bound to the request session.
    """

    return ProductRepository(session)


def get_transaction_repository(
    session: Session = Depends(get_db_session),
) -> TransactionRepository:
    """Provide a transaction repository bound to the request session.

    Args:
        session: Request-scoped SQLAlchemy session.

    Returns:
        A transaction repository bound to the request session.
    """

    return TransactionRepository(session)


def get_payment_repository(
    session: Session = Depends(get_db_session),
) -> PaymentRepository:
    """Provide a payment repository bound to the request session.

    Args:
        session: Request-scoped SQLAlchemy session.

    Returns:
        A payment repository bound to the request session.
    """

    return PaymentRepository(session)


def get_conversation_state_repository(
    session: Session = Depends(get_db_session),
) -> ConversationStateRepository:
    """Provide a conversation state repository bound to the request session.

    Args:
        session: Request-scoped SQLAlchemy session.

    Returns:
        A conversation state repository bound to the request session.
    """

    return ConversationStateRepository(session)


def get_authorized_user_repository(
    session: Session = Depends(get_db_session),
) -> AuthorizedUserRepository:
    """Provide an authorized user repository bound to the request session.

    Args:
        session: Request-scoped SQLAlchemy session.

    Returns:
        An authorized user repository bound to the request session.
    """

    return AuthorizedUserRepository(session)


def get_analytics_repository(
    session: Session = Depends(get_db_session),
) -> AnalyticsRepository:
    """Provide an analytics repository bound to the request session.

    Args:
        session: Request-scoped SQLAlchemy session.

    Returns:
        An analytics repository bound to the request session.
    """

    return AnalyticsRepository(session)


def get_balance_service(
    client_repository: ClientRepository = Depends(get_client_repository),
    transaction_repository: TransactionRepository = Depends(
        get_transaction_repository
    ),
    payment_repository: PaymentRepository = Depends(get_payment_repository),
) -> BalanceService:
    """Provide a balance service built from its repository dependencies.

    Args:
        client_repository: Repository used to validate customers.
        transaction_repository: Repository used to read active transactions.
        payment_repository: Repository used to read registered payments.

    Returns:
        A balance service ready to compute pending balances.
    """

    return BalanceService(
        client_repository, transaction_repository, payment_repository
    )


def get_conversation_state_service(
    conversation_state_repository: ConversationStateRepository = Depends(
        get_conversation_state_repository
    ),
) -> ConversationStateService:
    """Provide a conversation state service bound to its repository.

    Args:
        conversation_state_repository: Repository used for state persistence.

    Returns:
        A conversation state service ready to manage pending flows.
    """

    return ConversationStateService(conversation_state_repository)


def get_analytics_service(
    analytics_repository: AnalyticsRepository = Depends(get_analytics_repository),
) -> AnalyticsService:
    """Provide an analytics service bound to its repository.

    Args:
        analytics_repository: Repository used to fetch aggregate data.

    Returns:
        An analytics service ready to build historical reports.
    """

    return AnalyticsService(analytics_repository)


@dataclass(frozen=True, slots=True)
class ServiceContext:
    """Bundle of repositories and services required to handle one message.

    Args:
        client_repository: Repository used to resolve customers.
        product_repository: Repository used to resolve products.
        conversation_state_service: Service managing pending disambiguation flows.
        analytics_service: Service used to generate historical reports.
        balance_service: Service used to calculate balances.
        sale_service: Service used to register sales.
        payment_service: Service used to register payments.
        collection_summary_service: Service used to build collection summaries.
        transaction_cancellation_service: Service used to cancel transactions.
        product_price_service: Service used to update product prices.
    """

    client_repository: ClientRepository
    product_repository: ProductRepository
    conversation_state_service: ConversationStateService
    analytics_service: AnalyticsService
    balance_service: BalanceService
    sale_service: SaleService
    payment_service: PaymentService
    collection_summary_service: CollectionSummaryService
    transaction_cancellation_service: TransactionCancellationService
    product_price_service: ProductPriceService


# FastAPI dependency composition legitimately needs one parameter per
# collaborator being wired together.
# pylint: disable=too-many-positional-arguments
def get_service_context(
    client_repository: ClientRepository = Depends(get_client_repository),
    product_repository: ProductRepository = Depends(get_product_repository),
    transaction_repository: TransactionRepository = Depends(
        get_transaction_repository
    ),
    payment_repository: PaymentRepository = Depends(get_payment_repository),
    conversation_state_service: ConversationStateService = Depends(
        get_conversation_state_service
    ),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    balance_service: BalanceService = Depends(get_balance_service),
) -> ServiceContext:
    """Compose the full service context needed to handle one message.

    Args:
        client_repository: Repository used to resolve customers.
        product_repository: Repository used to resolve products.
        transaction_repository: Repository used for sales and cancellations.
        payment_repository: Repository used to persist payments.
        conversation_state_service: Service managing pending disambiguation flows.
        analytics_service: Service used to produce historical reports.
        balance_service: Service used to calculate balances.

    Returns:
        The composed service context for the current request.
    """

    return ServiceContext(
        client_repository=client_repository,
        product_repository=product_repository,
        conversation_state_service=conversation_state_service,
        analytics_service=analytics_service,
        balance_service=balance_service,
        sale_service=SaleService(
            client_repository,
            product_repository,
            transaction_repository,
            balance_service,
        ),
        payment_service=PaymentService(
            client_repository, payment_repository, balance_service
        ),
        collection_summary_service=CollectionSummaryService(
            client_repository,
            transaction_repository,
            payment_repository,
            balance_service,
        ),
        transaction_cancellation_service=TransactionCancellationService(
            transaction_repository, balance_service
        ),
        product_price_service=ProductPriceService(product_repository),
    )


def get_prompt_builder() -> PromptBuilder:
    """Provide the prompt builder used to assemble provider-agnostic prompts.

    Returns:
        A prompt builder reading assets from the default `/prompts` directory.
    """

    return PromptBuilder()


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Provide the configured LLM provider instance.

    Returns:
        The LLM provider selected through application configuration.

    Raises:
        ValueError: If the configured provider name is not supported.
    """

    return create_llm_provider(get_config())


def get_telegram_client(
    config: AppConfig = Depends(get_config),
) -> TelegramClient:
    """Provide a Telegram client configured with the bot token.

    Args:
        config: Application configuration holding the bot token.

    Returns:
        A Telegram client ready to send outbound messages.

    Raises:
        RuntimeError: If the Telegram bot token is not configured.
    """

    if not config.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

    return TelegramClient(bot_token=config.telegram_bot_token)
