"""OpenAI function calling format adapter.

OpenAI tool format (current):
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
}

Legacy function calling format (also supported):
{
    "name": "get_weather",
    "description": "...",
    "parameters": {...}
}
"""

from __future__ import annotations

from typing import Any

from aumai_protocolbridge.models import ToolDefinition


class OpenAIAdapter:
    """Adapter for OpenAI function/tool calling format."""

    def to_canonical(self, data: dict[str, Any]) -> ToolDefinition:
        """Convert OpenAI tool definition to canonical ToolDefinition.

        Handles both ``{"type": "function", "function": {...}}`` and
        legacy ``{"name": ..., "parameters": ...}`` forms.
        """
        # Unwrap tool wrapper if present
        if data.get("type") == "function" and "function" in data:
            func: dict[str, Any] = data["function"]
        else:
            func = data

        name: str = func.get("name", "")
        description: str = func.get("description", "")
        parameters: dict[str, Any] = func.get("parameters", {})

        return ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            returns={},
        )

    def from_canonical(self, tool: ToolDefinition) -> dict[str, Any]:
        """Convert canonical ToolDefinition to OpenAI tool format."""
        parameters = tool.parameters or {
            "type": "object",
            "properties": {},
        }
        # Ensure JSON Schema type is set
        if "type" not in parameters:
            parameters = {"type": "object", **parameters}

        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters,
            },
        }

    def message_to_canonical(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Convert an OpenAI chat message to canonical form."""
        role: str = msg.get("role", "user")
        content: str = msg.get("content") or ""
        tool_calls_raw: list[dict[str, Any]] = msg.get("tool_calls", [])

        canonical_tool_calls: list[dict[str, Any]] = []
        for tc in tool_calls_raw:
            func_block: dict[str, Any] = tc.get("function", {})
            import json as _json
            arguments_raw = func_block.get("arguments", "{}")
            try:
                arguments: dict[str, Any] = (
                    _json.loads(arguments_raw)
                    if isinstance(arguments_raw, str)
                    else arguments_raw
                )
            except _json.JSONDecodeError:
                arguments = {}
            canonical_tool_calls.append(
                {
                    "tool_name": func_block.get("name", ""),
                    "arguments": arguments,
                    "call_id": tc.get("id", ""),
                }
            )

        return {
            "role": role,
            "content": content,
            "tool_calls": canonical_tool_calls or None,
        }

    def message_from_canonical(self, canonical: dict[str, Any]) -> dict[str, Any]:
        """Convert canonical message dict to OpenAI format."""
        import json as _json

        role: str = canonical.get("role", "user")
        content: str = canonical.get("content") or ""
        tool_calls_raw: list[dict[str, Any]] = canonical.get("tool_calls") or []

        openai_tool_calls: list[dict[str, Any]] = [
            {
                "id": tc.get("call_id", ""),
                "type": "function",
                "function": {
                    "name": tc.get("tool_name", ""),
                    "arguments": _json.dumps(tc.get("arguments", {})),
                },
            }
            for tc in tool_calls_raw
        ]

        msg: dict[str, Any] = {"role": role, "content": content}
        if openai_tool_calls:
            msg["tool_calls"] = openai_tool_calls
        return msg


__all__ = ["OpenAIAdapter"]
