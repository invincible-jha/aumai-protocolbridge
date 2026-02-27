"""Tests for aumai_protocolbridge.models."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from aumai_protocolbridge.models import (
    Message,
    ProtocolType,
    ToolCall,
    ToolDefinition,
    ToolResult,
    TranslationResult,
)

# ---------------------------------------------------------------------------
# ProtocolType
# ---------------------------------------------------------------------------


class TestProtocolType:
    """Tests for the ProtocolType enum."""

    def test_all_four_protocols_exist(self) -> None:
        values = {p.value for p in ProtocolType}
        assert values == {"mcp", "a2a", "openai", "anthropic"}

    def test_protocol_type_is_string_enum(self) -> None:
        assert isinstance(ProtocolType.mcp, str)
        assert ProtocolType.openai == "openai"

    def test_protocol_type_from_string(self) -> None:
        assert ProtocolType("mcp") is ProtocolType.mcp
        assert ProtocolType("anthropic") is ProtocolType.anthropic

    def test_invalid_protocol_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            ProtocolType("unknown_protocol")


# ---------------------------------------------------------------------------
# ToolDefinition
# ---------------------------------------------------------------------------


class TestToolDefinition:
    """Tests for the ToolDefinition model."""

    def test_minimal_construction(self) -> None:
        tool = ToolDefinition(name="my_tool")
        assert tool.name == "my_tool"
        assert tool.description == ""
        assert tool.parameters == {}
        assert tool.returns == {}

    def test_full_construction(self) -> None:
        params: dict[str, Any] = {"type": "object", "properties": {}}
        returns: dict[str, Any] = {"type": "string"}
        tool = ToolDefinition(
            name="search",
            description="Run a search",
            parameters=params,
            returns=returns,
        )
        assert tool.name == "search"
        assert tool.description == "Run a search"
        assert tool.parameters == params
        assert tool.returns == returns

    def test_name_is_required(self) -> None:
        with pytest.raises(ValidationError):
            ToolDefinition()  # type: ignore[call-arg]

    def test_serialization_round_trip(self) -> None:
        tool = ToolDefinition(
            name="test",
            description="desc",
            parameters={"type": "object"},
        )
        data = tool.model_dump()
        restored = ToolDefinition(**data)
        assert restored == tool


# ---------------------------------------------------------------------------
# ToolCall
# ---------------------------------------------------------------------------


class TestToolCall:
    """Tests for the ToolCall model."""

    def test_construction(self) -> None:
        call = ToolCall(
            tool_name="get_weather", arguments={"city": "NYC"}, call_id="c1"
        )
        assert call.tool_name == "get_weather"
        assert call.arguments == {"city": "NYC"}
        assert call.call_id == "c1"

    def test_default_empty_arguments(self) -> None:
        call = ToolCall(tool_name="noop", call_id="c2")
        assert call.arguments == {}

    def test_all_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            ToolCall(tool_name="x")  # type: ignore[call-arg]  # missing call_id

    def test_serialization_round_trip(self) -> None:
        call = ToolCall(tool_name="fn", arguments={"k": "v"}, call_id="id1")
        restored = ToolCall(**call.model_dump())
        assert restored == call


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------


class TestToolResult:
    """Tests for the ToolResult model."""

    def test_success_result(self) -> None:
        result = ToolResult(call_id="c1", result={"output": 42})
        assert result.call_id == "c1"
        assert result.result == {"output": 42}
        assert result.error is None

    def test_error_result(self) -> None:
        result = ToolResult(call_id="c2", error="Timeout")
        assert result.error == "Timeout"
        assert result.result == {}

    def test_call_id_required(self) -> None:
        with pytest.raises(ValidationError):
            ToolResult()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


class TestMessage:
    """Tests for the Message model."""

    def test_user_message(self) -> None:
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_calls is None

    def test_assistant_message_with_tool_calls(self) -> None:
        calls = [ToolCall(tool_name="fn", call_id="c1")]
        msg = Message(role="assistant", content="", tool_calls=calls)
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1

    def test_role_required(self) -> None:
        with pytest.raises(ValidationError):
            Message()  # type: ignore[call-arg]

    def test_default_content_is_empty_string(self) -> None:
        msg = Message(role="system")
        assert msg.content == ""

    def test_system_message(self) -> None:
        msg = Message(role="system", content="You are a helpful assistant.")
        assert msg.role == "system"


# ---------------------------------------------------------------------------
# TranslationResult
# ---------------------------------------------------------------------------


class TestTranslationResult:
    """Tests for the TranslationResult model."""

    def test_construction(self) -> None:
        result = TranslationResult(
            source_protocol=ProtocolType.openai,
            target_protocol=ProtocolType.anthropic,
            original={"name": "fn"},
            translated={"name": "fn", "input_schema": {}},
        )
        assert result.source_protocol is ProtocolType.openai
        assert result.target_protocol is ProtocolType.anthropic
        assert result.warnings == []

    def test_with_warnings(self) -> None:
        result = TranslationResult(
            source_protocol=ProtocolType.mcp,
            target_protocol=ProtocolType.a2a,
            original={},
            translated={},
            warnings=["Tool name is empty."],
        )
        assert len(result.warnings) == 1
        assert "empty" in result.warnings[0]

    def test_all_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            TranslationResult(  # type: ignore[call-arg]
                source_protocol=ProtocolType.openai,
                target_protocol=ProtocolType.anthropic,
            )
