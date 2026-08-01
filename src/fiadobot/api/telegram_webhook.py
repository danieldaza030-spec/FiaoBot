"""FastAPI webhook endpoint that receives Telegram updates (RF09, RNF02).

Every request is validated against the authorized chat allow list before any
further processing happens. Once authorized, the message is handed off to
the framework-agnostic ``MessageOrchestrator`` to translate it into a tool
call, execute the corresponding service, and produce a reply.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status

from fiadobot.config import AppConfig
from fiadobot.llm.provider import LLMProvider
from fiadobot.prompting.prompt_builder import PromptBuilder
from fiadobot.repositories import AuthorizedUserRepository

from .auth import is_chat_authorized
from .dependencies import (
    ServiceContext,
    get_authorized_user_repository,
    get_config,
    get_llm_provider,
    get_prompt_builder,
    get_service_context,
    get_telegram_client,
)
from .message_orchestrator import MessageOrchestrator
from .telegram_client import TelegramClient
from .telegram_models import TelegramUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

_UNEXPECTED_ERROR_MESSAGE = (
    "Tuve un problema para procesar tu mensaje. Probá de nuevo en unos minutos."
)


# FastAPI endpoints legitimately need one parameter per injected dependency.
# pylint: disable=too-many-positional-arguments
@router.post("/telegram/webhook", status_code=status.HTTP_200_OK)
def receive_telegram_update(
    update: TelegramUpdate,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    config: AppConfig = Depends(get_config),
    authorized_user_repository: AuthorizedUserRepository = Depends(
        get_authorized_user_repository
    ),
    service_context: ServiceContext = Depends(get_service_context),
    prompt_builder: PromptBuilder = Depends(get_prompt_builder),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    telegram_client: TelegramClient = Depends(get_telegram_client),
) -> dict[str, str]:
    """Receive one Telegram update and dispatch the resulting reply.

    Args:
        update: Parsed Telegram update payload.
        x_telegram_bot_api_secret_token: Secret token Telegram sends back when
            a webhook secret was configured via ``setWebhook``.
        config: Application configuration used to validate the webhook secret.
        authorized_user_repository: Repository used to validate the chat_id.
        service_context: Bundle of repositories and services for this request.
        prompt_builder: Builder used to assemble the provider-agnostic prompt.
        llm_provider: Provider used to translate free text into a tool call.
        telegram_client: Client used to send the reply back to Telegram.

    Returns:
        A small status payload acknowledging the update.

    Raises:
        HTTPException: If the configured webhook secret does not match.
    """

    if config.telegram_webhook_secret and (
        x_telegram_bot_api_secret_token != config.telegram_webhook_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret token.",
        )

    if update.message is None or not update.message.text:
        return {"status": "ignored"}

    chat_id = update.message.chat.id
    if not is_chat_authorized(chat_id, authorized_user_repository):
        logger.warning("Rejected message from unauthorized chat_id=%s", chat_id)
        return {"status": "ignored"}

    orchestrator = MessageOrchestrator(service_context, prompt_builder, llm_provider)
    try:
        reply_text = orchestrator.handle_message(chat_id, update.message.text)
    except Exception:  # pylint: disable=broad-except
        # Last-resort safety net for unexpected infrastructure failures (LLM
        # provider outages, database connectivity issues, etc.). The vendor
        # still gets a reply and Telegram still gets a 200 acknowledgement,
        # instead of a silent 500 that would trigger webhook retries.
        logger.exception("Unexpected error handling chat_id=%s", chat_id)
        telegram_client.send_message(chat_id, _UNEXPECTED_ERROR_MESSAGE)
        return {"status": "error"}

    if reply_text:
        telegram_client.send_message(chat_id, reply_text)

    return {"status": "ok"}
