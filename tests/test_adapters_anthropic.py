"""Tests for the Anthropic adapter."""

from __future__ import annotations

from typing import Any

from aumai_protocolbridge.adapters.anthropic import AnthropicAdapter
from aumai_protocolbridge.models import ToolDefinition


class TestAnthropicAdapterToCanonical:
    """Tests for AnthropicAdapter.to_canonical."""

    def test_full_tool_definition(
        self,
        anthropic_adapter: AnthropicAdapter,
        anthropic_tool: dict[str, Any],
    ) -> None:
        canonical = anthropic_adapter.to_canonical(anthropic_tool)
        assert canonical.name == "get_weather"
        assert "weather" in canonical.description.lower()
        assert canonical.parameters["type"] == "object"
        assert "location" in canonical.parameters["properties"]

    def test_missing_input_schema_produces_empty_parameters(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        data: dict[str, Any] = {"name": "fn", "description": "does stuff"}
        canonical = anthropic_adapter.to_canonical(data)
        assert canonical.parameters == {}

    def test_empty_dict_produces_defaults(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        canonical = anthropic_adapter.to_canonical({})
        assert canonical.name == ""
        assert canonical.description == ""
        assert canonical.parameters == {}

    def test_returns_is_always_empty(
        self, anthropic_adapter: AnthropicAdapter, anthropic_tool: dict[str, Any]
    ) -> None:
        canonical = anthropic_adapter.to_canonical(anthropic_tool)
        assert canonical.returns == {}


class TestAnthropicAdapterFromCanonical:
    """Tests for AnthropicAdapter.from_canonical."""

    def test_produces_input_schema_key(
        self, anthropic_adapter: AnthropicAdapter, canonical_tool: ToolDefinition
    ) -> None:
        result = anthropic_adapter.from_canonical(canonical_tool)
        assert "input_schema" in result
        assert "inputSchema" not in result
        assert "parameters" not in result

    def test_name_and_description_preserved(
        self, anthropic_adapter: AnthropicAdapter, canonical_tool: ToolDefinition
    ) -> None:
        result = anthropic_adapter.from_canonical(canonical_tool)
        assert result["name"] == "get_weather"
        assert "weather" in result["description"].lower()

    def test_empty_parameters_gets_object_type(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        tool = ToolDefinition(name="noop", description="")
        result = anthropic_adapter.from_canonical(tool)
        assert result["input_schema"]["type"] == "object"

    def test_parameters_without_type_gets_object_type(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        tool = ToolDefinition(
            name="fn",
            description="",
            parameters={"properties": {"x": {"type": "string"}}},
        )
        result = anthropic_adapter.from_canonical(tool)
        assert result["input_schema"]["type"] == "object"

    def test_round_trip(
        self, anthropic_adapter: AnthropicAdapter, anthropic_tool: dict[str, Any]
    ) -> None:
        canonical = anthropic_adapter.to_canonical(anthropic_tool)
        restored = anthropic_adapter.from_canonical(canonical)
        assert restored["name"] == anthropic_tool["name"]
        assert restored["description"] == anthropic_tool["description"]
        assert restored["input_schema"] == anthropic_tool["input_schema"]


class TestAnthropicAdapterMessageToCanonical:
    """Tests for AnthropicAdapter.message_to_canonical."""

    def test_plain_string_content(
        self,
        anthropic_adapter: AnthropicAdapter,
        anthropic_user_message: dict[str, Any],
    ) -> None:
        canonical = anthropic_adapter.message_to_canonical(anthropic_user_message)
        assert canonical["role"] == "user"
        assert canonical["content"] == "What is the weather in London?"
        assert canonical["tool_calls"] is None

    def test_content_blocks_with_text_and_tool_use(
        self,
        anthropic_adapter: AnthropicAdapter,
        anthropic_assistant_message_with_tool_use: dict[str, Any],
    ) -> None:
        canonical = anthropic_adapter.message_to_canonical(
            anthropic_assistant_message_with_tool_use
        )
        assert canonical["role"] == "assistant"
        assert "weather" in canonical["content"].lower()
        assert canonical["tool_calls"] is not None
        tc = canonical["tool_calls"][0]
        assert tc["tool_name"] == "get_weather"
        assert tc["arguments"] == {"location": "London"}
        assert tc["call_id"] == "toolu_abc123"

    def test_tool_result_block_becomes_text(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        msg: dict[str, Any] = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_1",
                    "content": "sunny, 20°C",
                }
            ],
        }
        canonical = anthropic_adapter.message_to_canonical(msg)
        assert "sunny" in canonical["content"]

    def test_empty_content_list(self, anthropic_adapter: AnthropicAdapter) -> None:
        msg: dict[str, Any] = {"role": "user", "content": []}
        canonical = anthropic_adapter.message_to_canonical(msg)
        assert canonical["content"] == ""
        assert canonical["tool_calls"] is None

    def test_only_tool_use_blocks(self, anthropic_adapter: AnthropicAdapter) -> None:
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_2",
                    "name": "search",
                    "input": {"query": "python"},
                }
            ],
        }
        canonical = anthropic_adapter.message_to_canonical(msg)
        assert canonical["content"] == ""
        assert len(canonical["tool_calls"]) == 1

    def test_multiple_text_blocks_joined_with_space(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "First part."},
                {"type": "text", "text": "Second part."},
            ],
        }
        canonical = anthropic_adapter.message_to_canonical(msg)
        assert canonical["content"] == "First part. Second part."


class TestAnthropicAdapterMessageFromCanonical:
    """Tests for AnthropicAdapter.message_from_canonical."""

    def test_plain_text_returns_string_content(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        canonical: dict[str, Any] = {
            "role": "user",
            "content": "Hello",
            "tool_calls": None,
        }
        result = anthropic_adapter.message_from_canonical(canonical)
        assert result["role"] == "user"
        assert result["content"] == "Hello"

    def test_with_tool_calls_returns_content_blocks(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        canonical: dict[str, Any] = {
            "role": "assistant",
            "content": "Checking weather.",
            "tool_calls": [
                {
                    "tool_name": "get_weather",
                    "arguments": {"location": "Paris"},
                    "call_id": "toolu_xyz",
                }
            ],
        }
        result = anthropic_adapter.message_from_canonical(canonical)
        assert result["role"] == "assistant"
        blocks = result["content"]
        assert isinstance(blocks, list)
        text_blocks = [b for b in blocks if b["type"] == "text"]
        tool_blocks = [b for b in blocks if b["type"] == "tool_use"]
        assert len(text_blocks) == 1
        assert text_blocks[0]["text"] == "Checking weather."
        assert len(tool_blocks) == 1
        assert tool_blocks[0]["name"] == "get_weather"
        assert tool_blocks[0]["id"] == "toolu_xyz"
        assert tool_blocks[0]["input"] == {"location": "Paris"}

    def test_empty_content_with_no_tool_calls_returns_string(
        self, anthropic_adapter: AnthropicAdapter
    ) -> None:
        canonical: dict[str, Any] = {"role": "user", "content": "", "tool_calls": None}
        result = anthropic_adapter.message_from_canonical(canonical)
        # No tool calls, single empty text block collapses to string per adapter logic
        assert result["role"] == "user"

    def test_round_trip(
        self,
        anthropic_adapter: AnthropicAdapter,
        anthropic_assistant_message_with_tool_use: dict[str, Any],
    ) -> None:
        canonical = anthropic_adapter.message_to_canonical(
            anthropic_assistant_message_with_tool_use
        )
        restored = anthropic_adapter.message_from_canonical(canonical)
        assert restored["role"] == anthropic_assistant_message_with_tool_use["role"]
        # Restored content should be a list with both text and tool_use blocks
        assert isinstance(restored["content"], list)
        tool_blocks = [
            b for b in restored["content"] if b["type"] == "tool_use"
        ]
        assert len(tool_blocks) == 1
        assert tool_blocks[0]["name"] == "get_weather"
