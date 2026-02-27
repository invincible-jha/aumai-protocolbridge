"""Tests for the MCP adapter."""

from __future__ import annotations

from typing import Any

from aumai_protocolbridge.adapters.mcp import MCPAdapter
from aumai_protocolbridge.models import ToolDefinition


class TestMCPAdapterToCanonical:
    """Tests for MCPAdapter.to_canonical."""

    def test_full_tool_definition(
        self, mcp_adapter: MCPAdapter, mcp_tool: dict[str, Any]
    ) -> None:
        canonical = mcp_adapter.to_canonical(mcp_tool)
        assert canonical.name == "read_file"
        assert "Read" in canonical.description
        assert canonical.parameters["type"] == "object"
        assert "path" in canonical.parameters["properties"]

    def test_accepts_input_schema_snake_case(self, mcp_adapter: MCPAdapter) -> None:
        """MCP adapter must also accept snake_case input_schema as fallback."""
        data: dict[str, Any] = {
            "name": "list_files",
            "description": "List files in a directory.",
            "input_schema": {
                "type": "object",
                "properties": {"dir": {"type": "string"}},
            },
        }
        canonical = mcp_adapter.to_canonical(data)
        assert canonical.name == "list_files"
        assert "dir" in canonical.parameters["properties"]

    def test_camelcase_takes_priority_over_snake_case(
        self, mcp_adapter: MCPAdapter
    ) -> None:
        data: dict[str, Any] = {
            "name": "fn",
            "inputSchema": {"type": "object", "properties": {"a": {}}},
            "input_schema": {"type": "object", "properties": {"b": {}}},
        }
        canonical = mcp_adapter.to_canonical(data)
        # inputSchema (camelCase) should win
        assert "a" in canonical.parameters["properties"]

    def test_missing_fields_produce_defaults(self, mcp_adapter: MCPAdapter) -> None:
        canonical = mcp_adapter.to_canonical({})
        assert canonical.name == ""
        assert canonical.description == ""
        assert canonical.parameters == {}

    def test_returns_is_always_empty(
        self, mcp_adapter: MCPAdapter, mcp_tool: dict[str, Any]
    ) -> None:
        canonical = mcp_adapter.to_canonical(mcp_tool)
        assert canonical.returns == {}


class TestMCPAdapterFromCanonical:
    """Tests for MCPAdapter.from_canonical."""

    def test_produces_input_schema_key(
        self, mcp_adapter: MCPAdapter, canonical_tool: ToolDefinition
    ) -> None:
        result = mcp_adapter.from_canonical(canonical_tool)
        assert "inputSchema" in result
        assert "parameters" not in result

    def test_name_and_description_preserved(
        self, mcp_adapter: MCPAdapter, canonical_tool: ToolDefinition
    ) -> None:
        result = mcp_adapter.from_canonical(canonical_tool)
        assert result["name"] == "get_weather"
        assert "weather" in result["description"].lower()

    def test_empty_parameters_gets_object_type(self, mcp_adapter: MCPAdapter) -> None:
        tool = ToolDefinition(name="noop", description="")
        result = mcp_adapter.from_canonical(tool)
        assert result["inputSchema"]["type"] == "object"

    def test_parameters_without_type_gets_object_type(
        self, mcp_adapter: MCPAdapter
    ) -> None:
        tool = ToolDefinition(
            name="fn",
            description="",
            parameters={"properties": {"x": {"type": "string"}}},
        )
        result = mcp_adapter.from_canonical(tool)
        assert result["inputSchema"]["type"] == "object"

    def test_round_trip(
        self, mcp_adapter: MCPAdapter, mcp_tool: dict[str, Any]
    ) -> None:
        canonical = mcp_adapter.to_canonical(mcp_tool)
        restored = mcp_adapter.from_canonical(canonical)
        assert restored["name"] == mcp_tool["name"]
        assert restored["description"] == mcp_tool["description"]
        assert restored["inputSchema"] == mcp_tool["inputSchema"]


class TestMCPAdapterToolCall:
    """Tests for MCP tool call serialization / deserialization."""

    def test_tool_call_to_canonical_full_jsonrpc(
        self, mcp_adapter: MCPAdapter, mcp_tool_call: dict[str, Any]
    ) -> None:
        canonical = mcp_adapter.tool_call_to_canonical(mcp_tool_call)
        assert canonical["tool_name"] == "read_file"
        assert canonical["arguments"] == {"path": "/etc/hosts"}
        assert canonical["call_id"] == "call_1"

    def test_tool_call_to_canonical_bare_params(self, mcp_adapter: MCPAdapter) -> None:
        """When there is no JSON-RPC wrapper, treat the dict as params directly."""
        # Use a safe path string that does not trigger S108
        bare: dict[str, Any] = {
            "name": "read_file",
            "arguments": {"path": "/etc/hosts"},
        }
        canonical = mcp_adapter.tool_call_to_canonical(bare)
        assert canonical["tool_name"] == "read_file"
        assert canonical["arguments"] == {"path": "/etc/hosts"}

    def test_tool_call_from_canonical_produces_jsonrpc(
        self, mcp_adapter: MCPAdapter
    ) -> None:
        canonical: dict[str, Any] = {
            "tool_name": "read_file",
            "arguments": {"path": "/etc/hosts"},
            "call_id": "call_1",
        }
        result = mcp_adapter.tool_call_from_canonical(canonical)
        assert result["jsonrpc"] == "2.0"
        assert result["method"] == "tools/call"
        assert result["params"]["name"] == "read_file"
        assert result["params"]["arguments"] == {"path": "/etc/hosts"}
        assert result["id"] == "call_1"

    def test_tool_call_round_trip(
        self, mcp_adapter: MCPAdapter, mcp_tool_call: dict[str, Any]
    ) -> None:
        canonical = mcp_adapter.tool_call_to_canonical(mcp_tool_call)
        restored = mcp_adapter.tool_call_from_canonical(canonical)
        assert restored["params"]["name"] == mcp_tool_call["params"]["name"]
        assert (
            restored["params"]["arguments"]
            == mcp_tool_call["params"]["arguments"]
        )
        assert restored["id"] == mcp_tool_call["id"]

    def test_tool_call_from_canonical_empty_dict(self, mcp_adapter: MCPAdapter) -> None:
        result = mcp_adapter.tool_call_from_canonical({})
        assert result["jsonrpc"] == "2.0"
        assert result["params"]["name"] == ""
        assert result["params"]["arguments"] == {}


class TestMCPAdapterListToolsResponse:
    """Tests for MCPAdapter.list_tools_response_to_canonical."""

    def test_parses_result_tools_list(self, mcp_adapter: MCPAdapter) -> None:
        response: dict[str, Any] = {
            "result": {
                "tools": [
                    {"name": "fn1", "description": "d1", "inputSchema": {}},
                    {"name": "fn2", "description": "d2", "inputSchema": {}},
                ]
            }
        }
        tools = mcp_adapter.list_tools_response_to_canonical(response)
        assert len(tools) == 2
        assert tools[0].name == "fn1"
        assert tools[1].name == "fn2"

    def test_parses_bare_tools_list(self, mcp_adapter: MCPAdapter) -> None:
        response: dict[str, Any] = {
            "tools": [
                {"name": "fn3", "description": "d3", "inputSchema": {}}
            ]
        }
        tools = mcp_adapter.list_tools_response_to_canonical(response)
        assert len(tools) == 1
        assert tools[0].name == "fn3"

    def test_empty_response_returns_empty_list(self, mcp_adapter: MCPAdapter) -> None:
        tools = mcp_adapter.list_tools_response_to_canonical({})
        assert tools == []
