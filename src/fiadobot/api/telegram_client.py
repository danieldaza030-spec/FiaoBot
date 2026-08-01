"""Minimal Telegram Bot API client used to send outbound messages.

The client only knows how to call the Telegram HTTP API; it never decides
message content or business logic, which is assembled by the orchestrator.
"""

from __future__ import annotations

import httpx

# The client intentionally exposes a single outbound operation.
# pylint: disable=too-few-public-methods

TELEGRAM_API_BASE_URL = "https://api.telegram.org"
_REQUEST_TIMEOUT_SECONDS = 10.0


class TelegramClient:
    """Thin HTTP client for sending messages through the Telegram Bot API.

    Args:
        bot_token: Telegram bot token used to authenticate API calls.
        base_url: Base URL for the Telegram Bot API.
    """

    def __init__(
        self,
        bot_token: str,
        *,
        base_url: str = TELEGRAM_API_BASE_URL,
    ) -> None:
        """Initialize the client with the bot token and API base URL.

        Args:
            bot_token: Telegram bot token used to authenticate API calls.
            base_url: Base URL for the Telegram Bot API.

        Returns:
            None.

        Raises:
            None.
        """

        self.bot_token = bot_token
        self.base_url = base_url

    def send_message(self, chat_id: int, text: str) -> None:
        """Send a text message to a Telegram chat.

        Args:
            chat_id: Telegram chat identifier to message.
            text: Message body to send.

        Returns:
            None.

        Raises:
            httpx.HTTPError: If the request fails or Telegram returns an
                error status.
        """

        url = f"{self.base_url}/bot{self.bot_token}/sendMessage"
        response = httpx.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
