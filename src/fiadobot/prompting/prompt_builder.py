"""Build provider-agnostic prompt bundles from prompt assets and runtime context."""

from __future__ import annotations

import json
from pathlib import Path

from .types import PromptBundle, PromptContext, ToolDefinition, ToolSchema


class PromptBuilder:
    """Load prompt assets and assemble the final provider-agnostic payload."""

    def __init__(self, prompts_dir: Path | str | None = None) -> None:
        """Initialize the builder with the directory that stores prompt assets."""

        if prompts_dir is None:
            project_root = Path(__file__).resolve().parents[3]
            prompts_dir = project_root / "prompts"

        self.prompts_dir = Path(prompts_dir)

    def load_system_prompt(self) -> str:
        """Load the system prompt text from disk."""

        system_prompt_path = self.prompts_dir / "system_prompt.md"
        return system_prompt_path.read_text(encoding="utf-8").strip()

    def load_tool_schema(self) -> ToolSchema:
        """Load the canonical tool schema from disk."""

        schema_path = self.prompts_dir / "tools_schema.json"
        raw_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        tools = [
            ToolDefinition(
                name=tool_data["name"],
                description=tool_data["description"],
                parameters=tool_data["parameters"],
            )
            for tool_data in raw_schema["tools"]
        ]
        return ToolSchema(version=raw_schema["version"], tools=tools)

    def build(self, context: PromptContext) -> PromptBundle:
        """Build a prompt bundle for the provided runtime context."""

        system_prompt = self.load_system_prompt()
        tools = self.load_tool_schema()
        rendered_system_prompt = self._render_system_prompt(system_prompt, context)
        return PromptBundle(
            system_prompt=system_prompt,
            rendered_system_prompt=rendered_system_prompt,
            user_message=context.user_message,
            tools=tools,
            conversational_context=context.conversational_context,
            source_paths=(
                self.prompts_dir / "system_prompt.md",
                self.prompts_dir / "tools_schema.json",
            ),
        )

    def _render_system_prompt(self, system_prompt: str, context: PromptContext) -> str:
        """Append the runtime context to the system prompt as a JSON block."""

        runtime_context = {
            "channel": context.channel,
            "locale": context.locale,
            "conversation": context.conversational_context,
        }
        context_block = json.dumps(runtime_context, ensure_ascii=False, indent=2)
        return (
            f"{system_prompt}\n\n"
            f"## Runtime context\n\n"
            f"```json\n{context_block}\n```"
        )
