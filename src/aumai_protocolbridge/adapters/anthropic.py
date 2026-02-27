"""Anthropic tool use format adapter.

Anthropic tool format:
{
    "name": "get_weather",
    "description": "Get the current weather...",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"}
        },
        "required": ["location"]
    }
}

Tool use in messages:
{
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_abc123",
            "name": "get_weather",
            "input": {"location": "London"}
        }
    ]
}
"""

from __future__ import annotations

from typing import Any

from aumai_protocolbridge.models import ToolDefinition


class AnthropicAdapter:
    """Adapter for Anthropic tool use format."""

    def to_canonical(self, data: dict[str, Any]) -> ToolDefinition:
        """Convert Anthropic tool definition to canonical ToolDefinition."""
        name: str = data.get("name", "")
        description: str = data.get("description", "")
        input_schema: dict[str, Any] = data.get("input_schema", {})

        return ToolDefinition(
            name=name,
            description=description,
            parameters=input_schema,
            returns={},
        )

    def from_canonical(self, tool: ToolDefinition) -> dict[str, Any]:
        """Convert canonical ToolDefinition to Anthropic format."""
        input_schema = tool.parameters or {"type": "object", "properties": {}}
        if "type" not in input_schema:
            input_schema = {"type": "object", **input_schema}

        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": input_schema,
        }

    def message_to_canonical(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Convert an Anthropic message to canonical form.

        Anthropic messages may have content as a string or a list of blocks.
        """
        role: str = msg.get("role", "user")
        content_raw = msg.get("content", "")

        text_parts: list[str] = []
        canonical_tool_calls: list[dict[str, Any]] = []

        if isinstance(content_raw, str):
            text_parts.append(content_raw)
        elif isinstance(content_raw, list):
            for block in content_raw:
                block_type: str = block.get("type", "")
                if block_type == "text":
                    text_parts.append(block.get("text", ""))
                elif block_type == "tool_use":
                    canonical_tool_calls.append(
                        {
                            "tool_name": block.get("name", ""),
                            "arguments": block.get("input", {}),
                            "call_id": block.get("id", ""),
                        }
                    )
                elif block_type == "tool_result":
                    # Tool results are part of user messages in Anthropic format
                    text_parts.append(str(block.get("content", "")))

        # KNOWN LIMITATION: When an Anthropic message contains multiple content
        # blocks (e.g. interleaved text and tool_result blocks), all text-like
        # parts are collapsed into a single space-joined string in the canonical
        # "content" field.  Structural information about the original block
        # boundaries — such as which text block preceded which tool_result — is
        # not preserved.  Callers that need full fidelity for multi-block
        # messages should operate on the raw Anthropic format directly rather
        # than routing through the canonical representation.
        return {
            "role": role,
            "content": " ".join(text_parts),
            "tool_calls": canonical_tool_calls or None,
        }

    def message_from_canonical(self, canonical: dict[str, Any]) -> dict[str, Any]:
        """Convert canonical message dict to Anthropic format."""
        role: str = canonical.get("role", "user")
        content: str = canonical.get("content") or ""
        tool_calls_raw: list[dict[str, Any]] = canonical.get("tool_calls") or []

        content_blocks: list[dict[str, Any]] = []
        if content:
            content_blocks.append({"type": "text", "text": content})

        for tc in tool_calls_raw:
            content_blocks.append(
                {
                    "type": "tool_use",
                    "id": tc.get("call_id", ""),
                    "name": tc.get("tool_name", ""),
                    "input": tc.get("arguments", {}),
                }
            )

        if len(content_blocks) == 1 and content_blocks[0]["type"] == "text":
            return {"role": role, "content": content}

        return {"role": role, "content": content_blocks}


__all__ = ["AnthropicAdapter"]
