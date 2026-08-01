"""OpenAI adapter for the provider-agnostic LLM contract."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, OpenAIError

from fiadobot.prompting.types import PromptBundle, ToolDefinition

from .exceptions import LLMProviderError
from .provider import LLMProvider
from .types import ToolCall


class OpenAIProvider(LLMProvider):
    """Interpret prompt bundles using the OpenAI chat completions API.

    The adapter converts canonical prompt bundles into OpenAI messages and
    tool descriptors, then normalizes the returned tool call.
    """

    def __init__(self, client: Any, model: str) -> None:
        """Initialize the adapter with an OpenAI-compatible client.

        Args:
            client: OpenAI-compatible client instance.
            model: Model identifier used for chat completions.

        Returns:
            None.

        Raises:
            None.
        """

        self.client = client
        self.model = model

    @classmethod
    def from_api_key(cls, model: str, api_key: str | None = None) -> "OpenAIProvider":
        """Create an OpenAI provider using the official client and an API key.

        Args:
            model: Model identifier used for chat completions.
            api_key: Optional OpenAI API key.

        Returns:
            A configured OpenAI provider instance.
        """

        return cls(client=OpenAI(api_key=api_key), model=model)

    def interpret(self, prompt_bundle: PromptBundle) -> ToolCall:
        """Send the final prompt bundle to OpenAI and normalize the response.

        Args:
            prompt_bundle: Fully assembled prompt payload produced by the builder.

        Returns:
            A normalized tool call extracted from the provider response.

        Raises:
            LLMProviderError: If the OpenAI API call fails or returns a tool
                call whose arguments cannot be decoded as JSON.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(prompt_bundle),
                tools=self._build_tools(prompt_bundle.tools.tools),
                tool_choice="auto",
            )
        except OpenAIError as error:
            raise LLMProviderError(
                "OpenAI request failed while interpreting the message."
            ) from error

        message = response.choices[0].message
        assistant_message = message.content if message.content else None
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            tool_call = tool_calls[0]
            try:
                arguments = self._decode_arguments(tool_call.function.arguments)
            except json.JSONDecodeError as error:
                raise LLMProviderError(
                    "OpenAI returned tool call arguments that are not valid JSON."
                ) from error
            return ToolCall(
                tool_name=tool_call.function.name,
                arguments=arguments,
                assistant_message=assistant_message,
            )

        return ToolCall(
            tool_name=None,
            arguments={},
            assistant_message=assistant_message,
        )

    def _build_messages(self, prompt_bundle: PromptBundle) -> list[dict[str, str]]:
        """Build the chat messages expected by OpenAI from the prompt bundle.

        Args:
            prompt_bundle: Fully assembled prompt payload produced by the builder.

        Returns:
            The OpenAI message list containing system and user roles.
        """

        return [
            {"role": "system", "content": prompt_bundle.rendered_system_prompt},
            {"role": "user", "content": prompt_bundle.user_message},
        ]

    def _build_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert canonical tool definitions into OpenAI tool descriptors.

        Args:
            tools: Canonical tool definitions loaded from the prompt schema.

        Returns:
            The OpenAI tool descriptors for chat completions.
        """

        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    def _decode_arguments(self, arguments: str | None) -> dict[str, Any]:
        """Decode the JSON arguments payload returned by OpenAI.

        Args:
            arguments: Raw JSON string returned by the provider.

        Returns:
            The decoded arguments payload or an empty dictionary.

        Raises:
            json.JSONDecodeError: If the payload cannot be decoded.
        """

        if not arguments:
            return {}

        return json.loads(arguments)
