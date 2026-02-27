"""Tests for the A2A adapter."""

from __future__ import annotations

from typing import Any

from aumai_protocolbridge.adapters.a2a import A2AAdapter
from aumai_protocolbridge.models import ToolDefinition


class TestA2AAdapterToCanonical:
    """Tests for A2AAdapter.to_canonical."""

    def test_wrapped_skill_format(
        self, a2a_adapter: A2AAdapter, a2a_tool: dict[str, Any]
    ) -> None:
        canonical = a2a_adapter.to_canonical(a2a_tool)
        assert canonical.name == "search_web"
        assert "search" in canonical.description.lower()
        assert canonical.parameters["type"] == "object"
        assert "query" in canonical.parameters["properties"]

    def test_wrapped_skill_preserves_returns(
        self, a2a_adapter: A2AAdapter, a2a_tool: dict[str, Any]
    ) -> None:
        canonical = a2a_adapter.to_canonical(a2a_tool)
        assert canonical.returns != {}
        assert "results" in canonical.returns["properties"]

    def test_bare_skill_dict(self, a2a_adapter: A2AAdapter) -> None:
        """Bare skill dict (no 'skill' wrapper) should also be accepted."""
        bare: dict[str, Any] = {
            "name": "translate_text",
            "description": "Translate text to another language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "target_lang": {"type": "string"},
                },
            },
        }
        canonical = a2a_adapter.to_canonical(bare)
        assert canonical.name == "translate_text"
        assert "text" in canonical.parameters["properties"]

    def test_accepts_input_schema_as_fallback_for_parameters(
        self, a2a_adapter: A2AAdapter
    ) -> None:
        data: dict[str, Any] = {
            "skill": {
                "name": "fn",
                "description": "desc",
                "inputSchema": {
                    "type": "object",
                    "properties": {"x": {"type": "integer"}},
                },
            }
        }
        canonical = a2a_adapter.to_canonical(data)
        assert "x" in canonical.parameters["properties"]

    def test_empty_dict_produces_defaults(self, a2a_adapter: A2AAdapter) -> None:
        canonical = a2a_adapter.to_canonical({})
        assert canonical.name == ""
        assert canonical.description == ""
        assert canonical.parameters == {}
        assert canonical.returns == {}


class TestA2AAdapterFromCanonical:
    """Tests for A2AAdapter.from_canonical."""

    def test_produces_skill_wrapper(
        self, a2a_adapter: A2AAdapter, canonical_tool: ToolDefinition
    ) -> None:
        result = a2a_adapter.from_canonical(canonical_tool)
        assert "skill" in result
        skill = result["skill"]
        assert skill["name"] == "get_weather"
        assert "weather" in skill["description"].lower()

    def test_preserves_returns_when_present(
        self, a2a_adapter: A2AAdapter, canonical_tool: ToolDefinition
    ) -> None:
        result = a2a_adapter.from_canonical(canonical_tool)
        assert "returns" in result["skill"]

    def test_no_returns_field_when_empty(self, a2a_adapter: A2AAdapter) -> None:
        tool = ToolDefinition(name="noop", description="", returns={})
        result = a2a_adapter.from_canonical(tool)
        assert "returns" not in result["skill"]

    def test_empty_parameters_gets_object_type(self, a2a_adapter: A2AAdapter) -> None:
        tool = ToolDefinition(name="noop", description="")
        result = a2a_adapter.from_canonical(tool)
        assert result["skill"]["parameters"]["type"] == "object"

    def test_parameters_without_type_gets_object_type(
        self, a2a_adapter: A2AAdapter
    ) -> None:
        tool = ToolDefinition(
            name="fn",
            description="",
            parameters={"properties": {"x": {"type": "string"}}},
        )
        result = a2a_adapter.from_canonical(tool)
        assert result["skill"]["parameters"]["type"] == "object"

    def test_round_trip_wrapped_skill(
        self, a2a_adapter: A2AAdapter, a2a_tool: dict[str, Any]
    ) -> None:
        canonical = a2a_adapter.to_canonical(a2a_tool)
        restored = a2a_adapter.from_canonical(canonical)
        original_skill = a2a_tool["skill"]
        restored_skill = restored["skill"]
        assert restored_skill["name"] == original_skill["name"]
        assert restored_skill["description"] == original_skill["description"]
        assert restored_skill["parameters"] == original_skill["parameters"]


class TestA2AAdapterTaskCall:
    """Tests for A2AAdapter task call serialization / deserialization."""

    def test_task_call_to_canonical(
        self, a2a_adapter: A2AAdapter, a2a_task_call: dict[str, Any]
    ) -> None:
        canonical = a2a_adapter.task_call_to_canonical(a2a_task_call)
        assert canonical["tool_name"] == "search_web"
        assert canonical["arguments"] == {"query": "AI safety 2024"}
        assert canonical["call_id"] == "task_xyz"

    def test_task_call_to_canonical_with_name_fallback(
        self, a2a_adapter: A2AAdapter
    ) -> None:
        call: dict[str, Any] = {
            "name": "run_analysis",
            "arguments": {"data": [1, 2, 3]},
            "id": "t1",
        }
        canonical = a2a_adapter.task_call_to_canonical(call)
        assert canonical["tool_name"] == "run_analysis"
        assert canonical["call_id"] == "t1"

    def test_task_call_from_canonical(self, a2a_adapter: A2AAdapter) -> None:
        canonical: dict[str, Any] = {
            "tool_name": "search_web",
            "arguments": {"query": "test"},
            "call_id": "task_1",
        }
        result = a2a_adapter.task_call_from_canonical(canonical)
        assert result["task_id"] == "task_1"
        assert result["skill_name"] == "search_web"
        assert result["input"] == {"query": "test"}

    def test_task_call_round_trip(
        self, a2a_adapter: A2AAdapter, a2a_task_call: dict[str, Any]
    ) -> None:
        canonical = a2a_adapter.task_call_to_canonical(a2a_task_call)
        restored = a2a_adapter.task_call_from_canonical(canonical)
        assert restored["skill_name"] == a2a_task_call["skill_name"]
        assert restored["input"] == a2a_task_call["input"]
        assert restored["task_id"] == a2a_task_call["task_id"]

    def test_task_call_from_canonical_empty_dict(self, a2a_adapter: A2AAdapter) -> None:
        result = a2a_adapter.task_call_from_canonical({})
        assert result["task_id"] == ""
        assert result["skill_name"] == ""
        assert result["input"] == {}


class TestA2AAdapterAgentCard:
    """Tests for A2AAdapter.agent_card_tools_to_canonical."""

    def test_extracts_skills_from_agent_card(self, a2a_adapter: A2AAdapter) -> None:
        agent_card: dict[str, Any] = {
            "agent_id": "agent-001",
            "name": "Research Agent",
            "skills": [
                {
                    "name": "search_web",
                    "description": "Search the web.",
                    "parameters": {"type": "object", "properties": {"query": {}}},
                },
                {
                    "name": "summarize",
                    "description": "Summarise text.",
                    "parameters": {"type": "object", "properties": {"text": {}}},
                },
            ],
        }
        tools = a2a_adapter.agent_card_tools_to_canonical(agent_card)
        assert len(tools) == 2
        assert tools[0].name == "search_web"
        assert tools[1].name == "summarize"

    def test_empty_skills_returns_empty_list(self, a2a_adapter: A2AAdapter) -> None:
        tools = a2a_adapter.agent_card_tools_to_canonical({"skills": []})
        assert tools == []

    def test_no_skills_key_returns_empty_list(self, a2a_adapter: A2AAdapter) -> None:
        tools = a2a_adapter.agent_card_tools_to_canonical({})
        assert tools == []
