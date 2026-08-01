"""Unit tests for the OpenAI provider adapter's error normalization."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from openai import APIConnectionError

from fiadobot.llm.exceptions import LLMProviderError
from fiadobot.llm.openai_provider import OpenAIProvider
from fiadobot.prompting.types import PromptBundle, ToolSchema


def _build_prompt_bundle() -> PromptBundle:
    """Return a minimal prompt bundle with no tools for testing."""

    return PromptBundle(
        system_prompt="system",
        user_message="hola",
        rendered_system_prompt="system",
        tools=ToolSchema(version="1", tools=[]),
    )


def test_interpret_raises_llm_provider_error_on_api_failure() -> None:
    """It should wrap OpenAI SDK failures as a provider-agnostic error."""

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    )
    provider = OpenAIProvider(client=mock_client, model="gpt-4o-mini")

    with pytest.raises(LLMProviderError):
        provider.interpret(_build_prompt_bundle())


def test_interpret_raises_llm_provider_error_on_malformed_tool_arguments() -> None:
    """It should wrap malformed tool-call JSON as a provider-agnostic error."""

    tool_call = MagicMock()
    tool_call.function.name = "registrar_venta"
    tool_call.function.arguments = "{not-valid-json"

    message = MagicMock()
    message.content = None
    message.tool_calls = [tool_call]

    response = MagicMock()
    response.choices = [MagicMock(message=message)]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = response
    provider = OpenAIProvider(client=mock_client, model="gpt-4o-mini")

    with pytest.raises(LLMProviderError):
        provider.interpret(_build_prompt_bundle())
