"""Agent-to-Agent (A2A) protocol adapter.

A2A skill/tool format:
{
    "skill": {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        },
        "returns": {
            "type": "object",
            "properties": {
                "results": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
}

A2A task call format:
{
    "task_id": "task_abc",
    "skill_name": "search_web",
    "input": {"query": "AI safety 2024"}
}
"""

from __future__ import annotations

from typing import Any

from aumai_protocolbridge.models import ToolDefinition


class A2AAdapter:
    """Adapter for Agent-to-Agent (A2A) protocol format."""

    def to_canonical(self, data: dict[str, Any]) -> ToolDefinition:
        """Convert A2A skill definition to canonical ToolDefinition.

        Handles both wrapped ``{"skill": {...}}`` and bare skill dict forms.
        """
        skill: dict[str, Any] = data.get("skill", data)

        name: str = skill.get("name", "")
        description: str = skill.get("description", "")
        parameters: dict[str, Any] = skill.get(
            "parameters", skill.get("inputSchema", {})
        )
        returns: dict[str, Any] = skill.get("returns", skill.get("outputSchema", {}))

        return ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            returns=returns,
        )

    def from_canonical(self, tool: ToolDefinition) -> dict[str, Any]:
        """Convert canonical ToolDefinition to A2A skill format."""
        parameters = tool.parameters or {"type": "object", "properties": {}}
        if "type" not in parameters:
            parameters = {"type": "object", **parameters}

        skill: dict[str, Any] = {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters,
        }
        if tool.returns:
            skill["returns"] = tool.returns

        return {"skill": skill}

    def task_call_to_canonical(self, call: dict[str, Any]) -> dict[str, Any]:
        """Convert an A2A task call to canonical tool call form."""
        return {
            "tool_name": call.get("skill_name", call.get("name", "")),
            "arguments": call.get("input", call.get("arguments", {})),
            "call_id": call.get("task_id", call.get("id", "")),
        }

    def task_call_from_canonical(self, canonical: dict[str, Any]) -> dict[str, Any]:
        """Convert canonical tool call to A2A task call format."""
        return {
            "task_id": canonical.get("call_id", ""),
            "skill_name": canonical.get("tool_name", ""),
            "input": canonical.get("arguments", {}),
        }

    def agent_card_tools_to_canonical(
        self, agent_card: dict[str, Any]
    ) -> list[ToolDefinition]:
        """Extract tool definitions from an A2A agent card."""
        skills: list[dict[str, Any]] = agent_card.get("skills", [])
        return [self.to_canonical({"skill": s}) for s in skills]


__all__ = ["A2AAdapter"]
