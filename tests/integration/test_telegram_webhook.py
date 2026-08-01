"""Integration tests for the Telegram webhook wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fiadobot.api import telegram_router
from fiadobot.api.dependencies import (
    get_authorized_user_repository,
    get_config,
    get_llm_provider,
    get_prompt_builder,
    get_service_context,
    get_telegram_client,
)
from fiadobot.config import AppConfig
from fiadobot.llm.types import ToolCall


def _build_test_app() -> FastAPI:
    """Build a FastAPI app with the Telegram router mounted."""

    app = FastAPI()
    app.include_router(telegram_router)
    return app


def _build_fake_config() -> AppConfig:
    """Return a configuration object with webhook secret and bot token."""

    return AppConfig(
        app_name="fiadobot-test",
        environment="test",
        log_level="INFO",
        database_url="sqlite://",
        llm_provider="openai",
        openai_api_key="x",
        openai_model="gpt-4o-mini",
        telegram_bot_token="123:abc",
        telegram_webhook_secret="s3cret",
    )


def test_webhook_sends_reply_for_authorized_chat() -> None:
    """It should execute the flow and send a Telegram reply for authorized chats."""

    app = _build_test_app()
    fake_config = _build_fake_config()

    mock_authorized_repo = MagicMock()
    mock_authorized_repo.is_authorized.return_value = True

    mock_llm_provider = MagicMock()
    mock_llm_provider.interpret.return_value = ToolCall(
        tool_name=None,
        arguments={},
        assistant_message="Hola! En qué te ayudo?",
    )

    mock_conversation_state_service = MagicMock()
    mock_conversation_state_service.has_pending_state.return_value = False

    mock_service_context = MagicMock()
    mock_service_context.conversation_state_service = mock_conversation_state_service
    mock_prompt_builder = MagicMock()
    mock_prompt_builder.build.return_value = MagicMock()
    mock_telegram_client = MagicMock()

    app.dependency_overrides[get_config] = lambda: fake_config
    app.dependency_overrides[get_authorized_user_repository] = (
        lambda: mock_authorized_repo
    )
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm_provider
    app.dependency_overrides[get_service_context] = lambda: mock_service_context
    app.dependency_overrides[get_prompt_builder] = lambda: mock_prompt_builder
    app.dependency_overrides[get_telegram_client] = lambda: mock_telegram_client

    client = TestClient(app)
    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1, "message": {"chat": {"id": 555}, "text": "hola"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_telegram_client.send_message.assert_called_once_with(
        555,
        "Hola! En qué te ayudo?",
    )


def test_webhook_ignores_unauthorized_chat() -> None:
    """It should ignore unauthorized chats without sending a reply."""

    app = _build_test_app()
    fake_config = _build_fake_config()

    mock_authorized_repo = MagicMock()
    mock_authorized_repo.is_authorized.return_value = False

    mock_llm_provider = MagicMock()
    mock_conversation_state_service = MagicMock()
    mock_conversation_state_service.has_pending_state.return_value = False

    mock_service_context = MagicMock()
    mock_service_context.conversation_state_service = mock_conversation_state_service
    mock_prompt_builder = MagicMock()
    mock_telegram_client = MagicMock()

    app.dependency_overrides[get_config] = lambda: fake_config
    app.dependency_overrides[get_authorized_user_repository] = (
        lambda: mock_authorized_repo
    )
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm_provider
    app.dependency_overrides[get_service_context] = lambda: mock_service_context
    app.dependency_overrides[get_prompt_builder] = lambda: mock_prompt_builder
    app.dependency_overrides[get_telegram_client] = lambda: mock_telegram_client

    client = TestClient(app)
    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1, "message": {"chat": {"id": 555}, "text": "hola"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    mock_llm_provider.interpret.assert_not_called()
    mock_telegram_client.send_message.assert_not_called()


def test_webhook_replies_gracefully_on_unexpected_error() -> None:
    """It should ack the update and notify the vendor when handling fails."""

    app = _build_test_app()
    fake_config = _build_fake_config()

    mock_authorized_repo = MagicMock()
    mock_authorized_repo.is_authorized.return_value = True

    mock_llm_provider = MagicMock()
    mock_llm_provider.interpret.side_effect = RuntimeError("boom")

    mock_conversation_state_service = MagicMock()
    mock_conversation_state_service.has_pending_state.return_value = False

    mock_service_context = MagicMock()
    mock_service_context.conversation_state_service = mock_conversation_state_service
    mock_prompt_builder = MagicMock()
    mock_prompt_builder.build.return_value = MagicMock()
    mock_telegram_client = MagicMock()

    app.dependency_overrides[get_config] = lambda: fake_config
    app.dependency_overrides[get_authorized_user_repository] = (
        lambda: mock_authorized_repo
    )
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm_provider
    app.dependency_overrides[get_service_context] = lambda: mock_service_context
    app.dependency_overrides[get_prompt_builder] = lambda: mock_prompt_builder
    app.dependency_overrides[get_telegram_client] = lambda: mock_telegram_client

    client = TestClient(app)
    response = client.post(
        "/telegram/webhook",
        json={"update_id": 1, "message": {"chat": {"id": 555}, "text": "hola"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "error"}
    mock_telegram_client.send_message.assert_called_once()
    assert mock_telegram_client.send_message.call_args.args[0] == 555
