"""Tests for the OpenAI adapter."""

from __future__ import annotations

import json
from typing import Any

from aumai_protocolbridge.adapters.openai import OpenAIAdapter
from aumai_protocolbridge.models import ToolDefinition


class TestOpenAIAdapterToCanonical:
    """Tests for OpenAIAdapter.to_canonical."""

    def test_wrapped_tool_format(
        self, openai_adapter: OpenAIAdapter, openai_tool: dict[str, Any]
    ) -> None:
        canonical = openai_adapter.to_canonical(openai_tool)
        assert canonical.name == "get_weather"
        assert "weather" in canonical.description.lower()
        assert canonical.parameters["type"] == "object"
        assert "location" in canonical.parameters["properties"]

    def test_legacy_bare_function_format(
        self, openai_adapter: OpenAIAdapter, openai_legacy_tool: dict[str, Any]
    ) -> None:
        canonical = openai_adapter.to_canonical(openai_legacy_tool)
        assert canonical.name == "get_weather"
        assert "location" in canonical.parameters["properties"]

    def test_missing_fields_produce_defaults(
        self, openai_adapter: OpenAIAdapter
    ) -> None:
        canonical = openai_adapter.to_canonical({})
        assert canonical.name == ""
        assert canonical.description == ""
        assert canonical.parameters == {}

    def test_unwraps_only_when_type_is_function(
        self, openai_adapter: OpenAIAdapter
    ) -> None:
        data: dict[str, Any] = {
            "type": "retrieval",
            "function": {"name": "should_not_unwrap"},
        }
        canonical = openai_adapter.to_canonical(data)
        # type != "function" so should use bare form, not function sub-dict
        assert canonical.name == ""

    def test_returns_is_always_empty(
        self, openai_adapter: OpenAIAdapter, openai_tool: dict[str, Any]
    ) -> None:
        canonical = openai_adapter.to_canonical(openai_tool)
        assert canonical.returns == {}


class TestOpenAIAdapterFromCanonical:
    """Tests for OpenAIAdapter.from_canonical."""

    def test_produces_function_wrapper(
        self, openai_adapter: OpenAIAdapter, canonical_tool: ToolDefinition
    ) -> None:
        result = openai_adapter.from_canonical(canonical_tool)
        assert result["type"] == "function"
        assert "function" in result
        assert result["function"]["name"] == "get_weather"

    def test_parameters_preserved(
        self, openai_adapter: OpenAIAdapter, canonical_tool: ToolDefinition
    ) -> None:
        result = openai_adapter.from_canonical(canonical_tool)
        params = result["function"]["parameters"]
        assert "location" in params["properties"]

    def test_empty_parameters_gets_object_type(
        self, openai_adapter: OpenAIAdapter
    ) -> None:
        tool = ToolDefinition(name="noop", description="")
        result = openai_adapter.from_canonical(tool)
        assert result["function"]["parameters"]["type"] == "object"

    def test_parameters_without_type_gets_object_type(
        self, openai_adapter: OpenAIAdapter
    ) -> None:
        tool = ToolDefinition(
            name="fn",
            description="",
            parameters={"properties": {"x": {"type": "string"}}},
        )
        result = openai_adapter.from_canonical(tool)
        assert result["function"]["parameters"]["type"] == "object"

    def test_round_trip_wrapped_format(
        self, openai_adapter: OpenAIAdapter, openai_tool: dict[str, Any]
    ) -> None:
        canonical = openai_adapter.to_canonical(openai_tool)
        restored = openai_adapter.from_canonical(canonical)
        assert restored["type"] == "function"
        assert restored["function"]["name"] == openai_tool["function"]["name"]
        assert (
            restored["function"]["parameters"]
            == openai_tool["function"]["parameters"]
        )


class TestOpenAIAdapterMessageToCanonical:
    """Tests for OpenAIAdapter.message_to_canonical."""

    def test_plain_user_message(
        self,
        openai_adapter: OpenAIAdapter,
        openai_user_message: dict[str, Any],
    ) -> None:
        canonical = openai_adapter.message_to_canonical(openai_user_message)
        assert canonical["role"] == "user"
        assert canonical["content"] == "What is the weather in London?"
        assert canonical["tool_calls"] is None

    def test_assistant_message_with_tool_call(
        self,
        openai_adapter: OpenAIAdapter,
        openai_assistant_message_with_tool_call: dict[str, Any],
    ) -> None:
        canonical = openai_adapter.message_to_canonical(
            openai_assistant_message_with_tool_call
        )
        assert canonical["role"] == "assistant"
        assert canonical["tool_calls"] is not None
        assert len(canonical["tool_calls"]) == 1
        tc = canonical["tool_calls"][0]
        assert tc["tool_name"] == "get_weather"
        assert tc["arguments"]["location"] == "London"
        assert tc["call_id"] == "call_abc123"

    def test_none_content_becomes_empty_string(
        self, openai_adapter: OpenAIAdapter
    ) -> None:
        msg: dict[str, Any] = {"role": "assistant", "content": None}
        canonical = openai_adapter.message_to_canonical(msg)
        assert canonical["content"] == ""

    def test_malformed_arguments_json_defaults_to_empty_dict(
        self, openai_adapter: OpenAIAdapter
    ) -> None:
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {
                        "name": "fn",
                        "arguments": "NOT VALID JSON {{{",
                    },
                }
            ],
        }
        canonical = openai_adapter.message_to_canonical(msg)
        tc = canonical["tool_calls"][0]
        assert tc["arguments"] == {}

    def test_arguments_as_dict_passthrough(
        self, openai_adapter: OpenAIAdapter
    ) -> None:
        """arguments field that is already a dict (not a string) should work."""
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c2",
                    "type": "function",
                    "function": {
                        "name": "fn",
                        "arguments": {"key": "value"},
                    },
                }
            ],
        }
        canonical = openai_adapter.message_to_canonical(msg)
        assert canonical["tool_calls"][0]["arguments"] == {"key": "value"}

    def test_no_tool_calls_field(
        self, openai_adapter: OpenAIAdapter
    ) -> None:
        msg: dict[str, Any] = {"role": "user", "content": "hi"}
        canonical = openai_adapter.message_to_canonical(msg)
        assert canonical["tool_calls"] is None


class TestOpenAIAdapterMessageFromCanonical:
    """Tests for OpenAIAdapter.message_from_canonical."""

    def test_plain_message(self, openai_adapter: OpenAIAdapter) -> None:
        canonical: dict[str, Any] = {
            "role": "user",
            "content": "Hello",
            "tool_calls": None,
        }
        result = openai_adapter.message_from_canonical(canonical)
        assert result["role"] == "user"
        assert result["content"] == "Hello"
        assert "tool_calls" not in result

    def test_message_with_tool_calls(self, openai_adapter: OpenAIAdapter) -> None:
        canonical: dict[str, Any] = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "tool_name": "get_weather",
                    "arguments": {"location": "Paris"},
                    "call_id": "cid1",
                }
            ],
        }
        result = openai_adapter.message_from_canonical(canonical)
        assert result["role"] == "assistant"
        tc = result["tool_calls"][0]
        assert tc["id"] == "cid1"
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "get_weather"
        # arguments should be JSON-serialised string in OpenAI format
        assert json.loads(tc["function"]["arguments"]) == {"location": "Paris"}

    def test_message_round_trip(
        self,
        openai_adapter: OpenAIAdapter,
        openai_assistant_message_with_tool_call: dict[str, Any],
    ) -> None:
        canonical = openai_adapter.message_to_canonical(
            openai_assistant_message_with_tool_call
        )
        restored = openai_adapter.message_from_canonical(canonical)
        assert restored["role"] == openai_assistant_message_with_tool_call["role"]
        original_tc = openai_assistant_message_with_tool_call["tool_calls"][0]
        restored_tc = restored["tool_calls"][0]
        assert restored_tc["id"] == original_tc["id"]
        assert restored_tc["function"]["name"] == original_tc["function"]["name"]
