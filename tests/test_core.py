"""Tests for aumai_protocolbridge.core — registry, bridge, and translation."""

from __future__ import annotations

from typing import Any

import pytest

from aumai_protocolbridge.adapters.a2a import A2AAdapter
from aumai_protocolbridge.adapters.anthropic import AnthropicAdapter
from aumai_protocolbridge.adapters.mcp import MCPAdapter
from aumai_protocolbridge.adapters.openai import OpenAIAdapter
from aumai_protocolbridge.core import (
    AdapterRegistry,
    ProtocolAdapter,
    ProtocolBridge,
    _default_registry,
)
from aumai_protocolbridge.models import ProtocolType, ToolDefinition

# ---------------------------------------------------------------------------
# ProtocolAdapter structural type checks
# ---------------------------------------------------------------------------


class TestProtocolAdapterProtocol:
    """Ensure all concrete adapters satisfy the ProtocolAdapter structural type."""

    def test_mcp_adapter_satisfies_protocol(self) -> None:
        assert isinstance(MCPAdapter(), ProtocolAdapter)

    def test_openai_adapter_satisfies_protocol(self) -> None:
        assert isinstance(OpenAIAdapter(), ProtocolAdapter)

    def test_anthropic_adapter_satisfies_protocol(self) -> None:
        assert isinstance(AnthropicAdapter(), ProtocolAdapter)

    def test_a2a_adapter_satisfies_protocol(self) -> None:
        assert isinstance(A2AAdapter(), ProtocolAdapter)

    def test_arbitrary_object_does_not_satisfy_protocol(self) -> None:
        assert not isinstance(object(), ProtocolAdapter)

    def test_class_with_both_methods_satisfies_protocol(self) -> None:
        class MinimalAdapter:
            def to_canonical(self, data: dict[str, Any]) -> ToolDefinition:
                return ToolDefinition(name="x")

            def from_canonical(self, tool: ToolDefinition) -> dict[str, Any]:
                return {}

        assert isinstance(MinimalAdapter(), ProtocolAdapter)


# ---------------------------------------------------------------------------
# AdapterRegistry
# ---------------------------------------------------------------------------


class TestAdapterRegistry:
    """Tests for AdapterRegistry."""

    def test_register_and_get(self, registry: AdapterRegistry) -> None:
        adapter = registry.get(ProtocolType.openai)
        assert isinstance(adapter, OpenAIAdapter)

    def test_get_missing_protocol_raises_key_error(self) -> None:
        empty_registry = AdapterRegistry()
        with pytest.raises(KeyError, match="No adapter registered"):
            empty_registry.get(ProtocolType.mcp)

    def test_error_message_lists_available_protocols(self) -> None:
        reg = AdapterRegistry()
        reg.register(ProtocolType.openai, OpenAIAdapter())
        with pytest.raises(KeyError, match="openai"):
            reg.get(ProtocolType.mcp)

    def test_supported_protocols_returns_all_registered(
        self, registry: AdapterRegistry
    ) -> None:
        supported = set(registry.supported_protocols())
        assert supported == {
            ProtocolType.mcp,
            ProtocolType.openai,
            ProtocolType.anthropic,
            ProtocolType.a2a,
        }

    def test_register_overwrites_existing(self) -> None:
        reg = AdapterRegistry()
        adapter_v1 = MCPAdapter()
        adapter_v2 = MCPAdapter()
        reg.register(ProtocolType.mcp, adapter_v1)
        reg.register(ProtocolType.mcp, adapter_v2)
        assert reg.get(ProtocolType.mcp) is adapter_v2

    def test_empty_registry_returns_empty_list(self) -> None:
        reg = AdapterRegistry()
        assert reg.supported_protocols() == []


# ---------------------------------------------------------------------------
# _default_registry helper
# ---------------------------------------------------------------------------


class TestDefaultRegistry:
    """Tests for the _default_registry factory."""

    def test_all_four_protocols_registered(self) -> None:
        reg = _default_registry()
        supported = set(reg.supported_protocols())
        assert supported == {
            ProtocolType.mcp,
            ProtocolType.openai,
            ProtocolType.anthropic,
            ProtocolType.a2a,
        }

    def test_correct_adapter_types(self) -> None:
        reg = _default_registry()
        assert isinstance(reg.get(ProtocolType.mcp), MCPAdapter)
        assert isinstance(reg.get(ProtocolType.openai), OpenAIAdapter)
        assert isinstance(reg.get(ProtocolType.anthropic), AnthropicAdapter)
        assert isinstance(reg.get(ProtocolType.a2a), A2AAdapter)


# ---------------------------------------------------------------------------
# ProtocolBridge — translate_tool
# ---------------------------------------------------------------------------


class TestProtocolBridgeTranslateTool:
    """Tests for ProtocolBridge.translate_tool."""

    def test_openai_to_anthropic(
        self, bridge: ProtocolBridge, openai_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            openai_tool, ProtocolType.openai, ProtocolType.anthropic
        )
        assert result.source_protocol is ProtocolType.openai
        assert result.target_protocol is ProtocolType.anthropic
        assert result.translated["name"] == "get_weather"
        assert "input_schema" in result.translated

    def test_openai_to_mcp(
        self, bridge: ProtocolBridge, openai_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            openai_tool, ProtocolType.openai, ProtocolType.mcp
        )
        assert "inputSchema" in result.translated

    def test_openai_to_a2a(
        self, bridge: ProtocolBridge, openai_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            openai_tool, ProtocolType.openai, ProtocolType.a2a
        )
        assert "skill" in result.translated

    def test_anthropic_to_openai(
        self, bridge: ProtocolBridge, anthropic_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            anthropic_tool, ProtocolType.anthropic, ProtocolType.openai
        )
        assert result.translated["type"] == "function"
        assert "function" in result.translated

    def test_mcp_to_openai(
        self, bridge: ProtocolBridge, mcp_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            mcp_tool, ProtocolType.mcp, ProtocolType.openai
        )
        assert result.translated["type"] == "function"

    def test_mcp_to_anthropic(
        self, bridge: ProtocolBridge, mcp_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            mcp_tool, ProtocolType.mcp, ProtocolType.anthropic
        )
        assert "input_schema" in result.translated

    def test_a2a_to_mcp(
        self, bridge: ProtocolBridge, a2a_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            a2a_tool, ProtocolType.a2a, ProtocolType.mcp
        )
        assert "inputSchema" in result.translated

    def test_same_protocol_is_identity(
        self, bridge: ProtocolBridge, openai_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            openai_tool, ProtocolType.openai, ProtocolType.openai
        )
        assert result.translated["type"] == "function"
        assert result.translated["function"]["name"] == "get_weather"

    def test_original_is_preserved(
        self, bridge: ProtocolBridge, openai_tool: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool(
            openai_tool, ProtocolType.openai, ProtocolType.anthropic
        )
        # Pydantic stores original as a value copy; use equality not identity.
        assert result.original == openai_tool

    def test_empty_name_triggers_warning(self, bridge: ProtocolBridge) -> None:
        nameless: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": "",
                "description": "Something",
                "parameters": {},
            },
        }
        result = bridge.translate_tool(
            nameless, ProtocolType.openai, ProtocolType.mcp
        )
        assert any("name" in w.lower() for w in result.warnings)

    def test_empty_description_triggers_warning(self, bridge: ProtocolBridge) -> None:
        no_desc: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": "fn",
                "description": "",
                "parameters": {},
            },
        }
        result = bridge.translate_tool(
            no_desc, ProtocolType.openai, ProtocolType.mcp
        )
        assert any("description" in w.lower() for w in result.warnings)

    def test_unregistered_source_protocol_raises(self, bridge: ProtocolBridge) -> None:
        empty_reg = AdapterRegistry()
        bridge_empty = ProtocolBridge(registry=empty_reg)
        with pytest.raises(KeyError):
            bridge_empty.translate_tool({}, ProtocolType.openai, ProtocolType.mcp)

    def test_all_six_bidirectional_pairs(self, bridge: ProtocolBridge) -> None:
        """All 12 directed pairs among 4 protocols must succeed without exception."""
        protocols = list(ProtocolType)
        sample_tools = {
            ProtocolType.openai: {
                "type": "function",
                "function": {"name": "fn", "description": "d", "parameters": {}},
            },
            ProtocolType.anthropic: {
                "name": "fn",
                "description": "d",
                "input_schema": {"type": "object", "properties": {}},
            },
            ProtocolType.mcp: {
                "name": "fn",
                "description": "d",
                "inputSchema": {"type": "object", "properties": {}},
            },
            ProtocolType.a2a: {
                "skill": {
                    "name": "fn",
                    "description": "d",
                    "parameters": {"type": "object", "properties": {}},
                }
            },
        }
        for source in protocols:
            for target in protocols:
                result = bridge.translate_tool(
                    sample_tools[source], source, target
                )
                assert result.source_protocol is source
                assert result.target_protocol is target


# ---------------------------------------------------------------------------
# ProtocolBridge — translate_message
# ---------------------------------------------------------------------------


class TestProtocolBridgeTranslateMessage:
    """Tests for ProtocolBridge.translate_message."""

    def test_openai_to_anthropic_plain_message(
        self,
        bridge: ProtocolBridge,
        openai_user_message: dict[str, Any],
    ) -> None:
        result = bridge.translate_message(
            openai_user_message, ProtocolType.openai, ProtocolType.anthropic
        )
        assert result.translated["role"] == "user"
        # Anthropic plain text message uses a string content
        assert result.translated["content"] == "What is the weather in London?"

    def test_openai_to_anthropic_with_tool_call(
        self,
        bridge: ProtocolBridge,
        openai_assistant_message_with_tool_call: dict[str, Any],
    ) -> None:
        result = bridge.translate_message(
            openai_assistant_message_with_tool_call,
            ProtocolType.openai,
            ProtocolType.anthropic,
        )
        assert result.translated["role"] == "assistant"
        content = result.translated["content"]
        assert isinstance(content, list)
        tool_blocks = [b for b in content if b["type"] == "tool_use"]
        assert len(tool_blocks) == 1
        assert tool_blocks[0]["name"] == "get_weather"

    def test_anthropic_to_openai_plain_message(
        self,
        bridge: ProtocolBridge,
        anthropic_user_message: dict[str, Any],
    ) -> None:
        result = bridge.translate_message(
            anthropic_user_message, ProtocolType.anthropic, ProtocolType.openai
        )
        assert result.translated["role"] == "user"
        assert result.translated["content"] == "What is the weather in London?"

    def test_anthropic_to_openai_with_tool_use(
        self,
        bridge: ProtocolBridge,
        anthropic_assistant_message_with_tool_use: dict[str, Any],
    ) -> None:
        result = bridge.translate_message(
            anthropic_assistant_message_with_tool_use,
            ProtocolType.anthropic,
            ProtocolType.openai,
        )
        assert "tool_calls" in result.translated
        tc = result.translated["tool_calls"][0]
        assert tc["function"]["name"] == "get_weather"

    def test_fallback_generic_message_conversion(self, bridge: ProtocolBridge) -> None:
        """Adapters without message_to_canonical trigger the generic fallback."""
        # MCP adapter has no message methods — forces generic path
        msg: dict[str, Any] = {"role": "user", "content": "hello"}
        result = bridge.translate_message(msg, ProtocolType.mcp, ProtocolType.openai)
        assert any("generic fallback" in w for w in result.warnings)
        assert result.translated["role"] == "user"

    def test_fallback_target_with_no_from_canonical(
        self, bridge: ProtocolBridge
    ) -> None:
        """Adapters without message_from_canonical return canonical form + warning."""
        msg: dict[str, Any] = {"role": "user", "content": "hello"}
        result = bridge.translate_message(msg, ProtocolType.openai, ProtocolType.mcp)
        assert any("canonical form" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# ProtocolBridge — translate_tool_call
# ---------------------------------------------------------------------------


class TestProtocolBridgeTranslateToolCall:
    """Tests for ProtocolBridge.translate_tool_call."""

    def test_mcp_to_a2a(
        self, bridge: ProtocolBridge, mcp_tool_call: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool_call(
            mcp_tool_call, ProtocolType.mcp, ProtocolType.a2a
        )
        assert result.translated["skill_name"] == "read_file"
        assert result.translated["input"] == {"path": "/etc/hosts"}
        assert result.translated["task_id"] == "call_1"

    def test_a2a_to_mcp(
        self, bridge: ProtocolBridge, a2a_task_call: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool_call(
            a2a_task_call, ProtocolType.a2a, ProtocolType.mcp
        )
        assert result.translated["jsonrpc"] == "2.0"
        assert result.translated["params"]["name"] == "search_web"

    def test_source_with_no_deserializer_passthrough(
        self, bridge: ProtocolBridge
    ) -> None:
        """OpenAI adapter has no tool_call_to_canonical; call passes through."""
        call: dict[str, Any] = {
            "id": "c1",
            "type": "function",
            "function": {"name": "fn"},
        }
        result = bridge.translate_tool_call(
            call, ProtocolType.openai, ProtocolType.mcp
        )
        assert any("unchanged" in w for w in result.warnings)

    def test_original_is_preserved(
        self, bridge: ProtocolBridge, mcp_tool_call: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool_call(
            mcp_tool_call, ProtocolType.mcp, ProtocolType.a2a
        )
        # Pydantic stores original as a value copy; use equality not identity.
        assert result.original == mcp_tool_call

    def test_mcp_to_mcp_round_trip(
        self, bridge: ProtocolBridge, mcp_tool_call: dict[str, Any]
    ) -> None:
        result = bridge.translate_tool_call(
            mcp_tool_call, ProtocolType.mcp, ProtocolType.mcp
        )
        assert result.translated["params"]["name"] == "read_file"
        assert result.translated["id"] == "call_1"


# ---------------------------------------------------------------------------
# ProtocolBridge — validate_tool
# ---------------------------------------------------------------------------


class TestProtocolBridgeValidateTool:
    """Tests for ProtocolBridge.validate_tool."""

    def test_valid_openai_tool_returns_no_issues(
        self, bridge: ProtocolBridge, openai_tool: dict[str, Any]
    ) -> None:
        issues = bridge.validate_tool(openai_tool, ProtocolType.openai)
        assert issues == []

    def test_valid_anthropic_tool_returns_no_issues(
        self, bridge: ProtocolBridge, anthropic_tool: dict[str, Any]
    ) -> None:
        issues = bridge.validate_tool(anthropic_tool, ProtocolType.anthropic)
        assert issues == []

    def test_valid_mcp_tool_returns_no_issues(
        self, bridge: ProtocolBridge, mcp_tool: dict[str, Any]
    ) -> None:
        issues = bridge.validate_tool(mcp_tool, ProtocolType.mcp)
        assert issues == []

    def test_valid_a2a_tool_returns_no_issues(
        self, bridge: ProtocolBridge, a2a_tool: dict[str, Any]
    ) -> None:
        issues = bridge.validate_tool(a2a_tool, ProtocolType.a2a)
        assert issues == []

    def test_anthropic_tool_missing_input_schema(self, bridge: ProtocolBridge) -> None:
        bad: dict[str, Any] = {"name": "fn", "description": "d"}
        issues = bridge.validate_tool(bad, ProtocolType.anthropic)
        assert any("input_schema" in i for i in issues)

    def test_mcp_tool_missing_input_schema(self, bridge: ProtocolBridge) -> None:
        bad: dict[str, Any] = {"name": "fn", "description": "d"}
        issues = bridge.validate_tool(bad, ProtocolType.mcp)
        assert any("inputSchema" in i for i in issues)

    def test_a2a_tool_missing_skill_and_name(self, bridge: ProtocolBridge) -> None:
        bad: dict[str, Any] = {"description": "no name"}
        issues = bridge.validate_tool(bad, ProtocolType.a2a)
        assert any("skill" in i.lower() or "name" in i.lower() for i in issues)

    def test_openai_tool_missing_type_wrapper(self, bridge: ProtocolBridge) -> None:
        bare: dict[str, Any] = {"name": "fn", "description": "d", "parameters": {}}
        issues = bridge.validate_tool(bare, ProtocolType.openai)
        assert any("type" in i.lower() or "function" in i.lower() for i in issues)

    def test_nameless_tool_reports_missing_name(self, bridge: ProtocolBridge) -> None:
        nameless: dict[str, Any] = {
            "type": "function",
            "function": {"name": "", "description": "d", "parameters": {}},
        }
        issues = bridge.validate_tool(nameless, ProtocolType.openai)
        assert any("name" in i.lower() for i in issues)

    def test_unregistered_protocol_raises(self, bridge: ProtocolBridge) -> None:
        empty_reg = AdapterRegistry()
        bridge_empty = ProtocolBridge(registry=empty_reg)
        with pytest.raises(KeyError):
            bridge_empty.validate_tool({}, ProtocolType.openai)


# ---------------------------------------------------------------------------
# ProtocolBridge — _generic_message_to_canonical static helper
# ---------------------------------------------------------------------------


class TestGenericMessageToCanonical:
    """Tests for the static _generic_message_to_canonical helper."""

    def test_extracts_role_and_content(self) -> None:
        result = ProtocolBridge._generic_message_to_canonical(
            {"role": "assistant", "content": "hi"}
        )
        assert result["role"] == "assistant"
        assert result["content"] == "hi"
        assert result["tool_calls"] is None

    def test_defaults_role_to_user(self) -> None:
        result = ProtocolBridge._generic_message_to_canonical({})
        assert result["role"] == "user"

    def test_converts_non_string_content(self) -> None:
        result = ProtocolBridge._generic_message_to_canonical(
            {"role": "user", "content": 42}
        )
        assert result["content"] == "42"


# ---------------------------------------------------------------------------
# ProtocolBridge — custom registry injection
# ---------------------------------------------------------------------------


class TestProtocolBridgeCustomRegistry:
    """Tests for injecting a custom registry into ProtocolBridge."""

    def test_custom_registry_is_used(self) -> None:
        custom_reg = AdapterRegistry()
        custom_reg.register(ProtocolType.openai, OpenAIAdapter())
        bridge = ProtocolBridge(registry=custom_reg)
        assert ProtocolType.mcp not in bridge._registry.supported_protocols()  # noqa: SLF001

    def test_default_registry_is_created_when_none_passed(self) -> None:
        bridge = ProtocolBridge()
        supported = set(bridge._registry.supported_protocols())  # noqa: SLF001
        assert len(supported) == 4
