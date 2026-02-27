"""Shared test fixtures for aumai-protocolbridge tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aumai_protocolbridge.adapters.a2a import A2AAdapter
from aumai_protocolbridge.adapters.anthropic import AnthropicAdapter
from aumai_protocolbridge.adapters.mcp import MCPAdapter
from aumai_protocolbridge.adapters.openai import OpenAIAdapter
from aumai_protocolbridge.core import AdapterRegistry, ProtocolBridge
from aumai_protocolbridge.models import ProtocolType, ToolDefinition

# ---------------------------------------------------------------------------
# Adapter fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mcp_adapter() -> MCPAdapter:
    """Return a fresh MCPAdapter instance."""
    return MCPAdapter()


@pytest.fixture()
def openai_adapter() -> OpenAIAdapter:
    """Return a fresh OpenAIAdapter instance."""
    return OpenAIAdapter()


@pytest.fixture()
def anthropic_adapter() -> AnthropicAdapter:
    """Return a fresh AnthropicAdapter instance."""
    return AnthropicAdapter()


@pytest.fixture()
def a2a_adapter() -> A2AAdapter:
    """Return a fresh A2AAdapter instance."""
    return A2AAdapter()


# ---------------------------------------------------------------------------
# Registry / Bridge fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def registry() -> AdapterRegistry:
    """Return an AdapterRegistry pre-populated with all built-in adapters."""
    reg = AdapterRegistry()
    reg.register(ProtocolType.mcp, MCPAdapter())
    reg.register(ProtocolType.openai, OpenAIAdapter())
    reg.register(ProtocolType.anthropic, AnthropicAdapter())
    reg.register(ProtocolType.a2a, A2AAdapter())
    return reg


@pytest.fixture()
def bridge() -> ProtocolBridge:
    """Return a ProtocolBridge using the default registry."""
    return ProtocolBridge()


# ---------------------------------------------------------------------------
# Canonical tool definition fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def canonical_tool() -> ToolDefinition:
    """Return a fully-populated canonical ToolDefinition."""
    return ToolDefinition(
        name="get_weather",
        description="Get current weather for a location.",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit",
                },
            },
            "required": ["location"],
        },
        returns={
            "type": "object",
            "properties": {
                "temperature": {"type": "number"},
                "condition": {"type": "string"},
            },
        },
    )


@pytest.fixture()
def minimal_canonical_tool() -> ToolDefinition:
    """Return a minimal canonical ToolDefinition with only a name."""
    return ToolDefinition(name="noop", description="", parameters={}, returns={})


# ---------------------------------------------------------------------------
# Protocol-specific raw tool dict fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def openai_tool() -> dict[str, Any]:
    """Return a well-formed OpenAI tool definition dict."""
    return {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["location"],
            },
        },
    }


@pytest.fixture()
def openai_legacy_tool() -> dict[str, Any]:
    """Return a legacy (bare function) OpenAI tool definition dict."""
    return {
        "name": "get_weather",
        "description": "Get current weather.",
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    }


@pytest.fixture()
def anthropic_tool() -> dict[str, Any]:
    """Return a well-formed Anthropic tool definition dict."""
    return {
        "name": "get_weather",
        "description": "Get current weather for a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
            },
            "required": ["location"],
        },
    }


@pytest.fixture()
def mcp_tool() -> dict[str, Any]:
    """Return a well-formed MCP tool definition dict."""
    return {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
            },
            "required": ["path"],
        },
    }


@pytest.fixture()
def a2a_tool() -> dict[str, Any]:
    """Return a well-formed A2A skill dict (wrapped form)."""
    return {
        "skill": {
            "name": "search_web",
            "description": "Search the web for information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
            "returns": {
                "type": "object",
                "properties": {
                    "results": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    }


# ---------------------------------------------------------------------------
# Message dict fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def openai_user_message() -> dict[str, Any]:
    """Return an OpenAI user message dict."""
    return {"role": "user", "content": "What is the weather in London?"}


@pytest.fixture()
def openai_assistant_message_with_tool_call() -> dict[str, Any]:
    """Return an OpenAI assistant message that includes a tool call."""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "London", "units": "celsius"}',
                },
            }
        ],
    }


@pytest.fixture()
def anthropic_user_message() -> dict[str, Any]:
    """Return an Anthropic user message with a string content."""
    return {"role": "user", "content": "What is the weather in London?"}


@pytest.fixture()
def anthropic_assistant_message_with_tool_use() -> dict[str, Any]:
    """Return an Anthropic assistant message with tool_use content blocks."""
    return {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Let me check the weather."},
            {
                "type": "tool_use",
                "id": "toolu_abc123",
                "name": "get_weather",
                "input": {"location": "London"},
            },
        ],
    }


# ---------------------------------------------------------------------------
# Tool call dict fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mcp_tool_call() -> dict[str, Any]:
    """Return a well-formed MCP tool call (JSON-RPC style)."""
    return {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "read_file",
            "arguments": {"path": "/etc/hosts"},
        },
        "id": "call_1",
    }


@pytest.fixture()
def a2a_task_call() -> dict[str, Any]:
    """Return a well-formed A2A task call dict."""
    return {
        "task_id": "task_xyz",
        "skill_name": "search_web",
        "input": {"query": "AI safety 2024"},
    }


# ---------------------------------------------------------------------------
# Temporary JSON file helper
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_json_file(tmp_path: Path):  # type: ignore[type-arg]
    """Return a factory that writes a dict to a temp JSON file and returns the Path."""

    def _factory(data: dict[str, Any], filename: str = "input.json") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(json.dumps(data), encoding="utf-8")
        return file_path

    return _factory
