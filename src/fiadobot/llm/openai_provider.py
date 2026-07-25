"""OpenAI adapter for the provider-agnostic LLM contract."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from fiadobot.prompting.types import PromptBundle, ToolDefinition

from .provider import LLMProvider
from .types import ToolCall


class OpenAIProvider(LLMProvider):
    """Interpret prompt bundles using the OpenAI chat completions API."""

    def __init__(self, client: Any, model: str) -> None:
        """Initialize the adapter with an OpenAI-compatible client."""

        self.client = client
        self.model = model

    @classmethod
    def from_api_key(cls, model: str, api_key: str | None = None) -> "OpenAIProvider":
        """Create an OpenAI provider using the official client and an API key."""

        return cls(client=OpenAI(api_key=api_key), model=model)

    def interpret(self, prompt_bundle: PromptBundle) -> ToolCall:
        """Send the final prompt bundle to OpenAI and normalize the response."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt_bundle),
            tools=self._build_tools(prompt_bundle.tools.tools),
            tool_choice="auto",
        )
        message = response.choices[0].message
        assistant_message = message.content if message.content else None
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            tool_call = tool_calls[0]
            arguments = self._decode_arguments(tool_call.function.arguments)
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
        """Build the chat messages expected by OpenAI from the prompt bundle."""

        return [
            {"role": "system", "content": prompt_bundle.rendered_system_prompt},
            {"role": "user", "content": prompt_bundle.user_message},
        ]

    def _build_tools(self, tools: list[ToolDefinition]) -> list[dict[str, Any]]:
        """Convert canonical tool definitions into OpenAI tool descriptors."""

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
        """Decode the JSON arguments payload returned by OpenAI."""

        if not arguments:
            return {}

        return json.loads(arguments)
