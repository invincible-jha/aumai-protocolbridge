"""MCP (Model Context Protocol) tool format adapter.

MCP tool format:
{
    "name": "read_file",
    "description": "Read the contents of a file",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"}
        },
        "required": ["path"]
    }
}

MCP uses camelCase ``inputSchema`` (not ``input_schema`` or ``parameters``).

Tool call format (JSON-RPC style):
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "read_file",
        "arguments": {"path": "/etc/hosts"}
    },
    "id": "call_1"
}
"""

from __future__ import annotations

from typing import Any

from aumai_protocolbridge.models import ToolDefinition


class MCPAdapter:
    """Adapter for MCP (Model Context Protocol) tool format."""

    def to_canonical(self, data: dict[str, Any]) -> ToolDefinition:
        """Convert MCP tool definition to canonical ToolDefinition."""
        name: str = data.get("name", "")
        description: str = data.get("description", "")
        # MCP uses camelCase ``inputSchema``
        input_schema: dict[str, Any] = data.get(
            "inputSchema", data.get("input_schema", {})
        )

        return ToolDefinition(
            name=name,
            description=description,
            parameters=input_schema,
            returns={},
        )

    def from_canonical(self, tool: ToolDefinition) -> dict[str, Any]:
        """Convert canonical ToolDefinition to MCP format."""
        input_schema = tool.parameters or {"type": "object", "properties": {}}
        if "type" not in input_schema:
            input_schema = {"type": "object", **input_schema}

        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": input_schema,
        }

    def tool_call_to_canonical(self, call: dict[str, Any]) -> dict[str, Any]:
        """Convert an MCP tool call (JSON-RPC params) to canonical form."""
        # MCP JSON-RPC: { "method": "tools/call", "params": {...}, "id": ... }
        params: dict[str, Any] = call.get("params", call)
        call_id: str = str(call.get("id", ""))

        return {
            "tool_name": params.get("name", ""),
            "arguments": params.get("arguments", {}),
            "call_id": call_id,
        }

    def tool_call_from_canonical(self, canonical: dict[str, Any]) -> dict[str, Any]:
        """Convert canonical tool call to MCP JSON-RPC format."""
        return {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": canonical.get("tool_name", ""),
                "arguments": canonical.get("arguments", {}),
            },
            "id": canonical.get("call_id", ""),
        }

    def list_tools_response_to_canonical(
        self, response: dict[str, Any]
    ) -> list[ToolDefinition]:
        """Parse a ``tools/list`` response into ToolDefinition objects."""
        tools_list: list[dict[str, Any]] = response.get("result", {}).get(
            "tools", response.get("tools", [])
        )
        return [self.to_canonical(t) for t in tools_list]


__all__ = ["MCPAdapter"]
