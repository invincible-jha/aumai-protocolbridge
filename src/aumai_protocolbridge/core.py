"""Core bridge logic: adapter registry, protocol translation."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from aumai_protocolbridge.models import (
    ProtocolType,
    ToolDefinition,
    TranslationResult,
)


@runtime_checkable
class ProtocolAdapter(Protocol):
    """Protocol (structural type) that all adapters must satisfy."""

    def to_canonical(self, data: dict[str, Any]) -> ToolDefinition:
        """Convert a protocol-specific tool dict to canonical ToolDefinition."""
        ...

    def from_canonical(self, tool: ToolDefinition) -> dict[str, Any]:
        """Convert a canonical ToolDefinition to the protocol-specific format."""
        ...


class AdapterRegistry:
    """Registry that maps ProtocolType to adapter instances."""

    def __init__(self) -> None:
        self._adapters: dict[ProtocolType, ProtocolAdapter] = {}

    def register(self, protocol: ProtocolType, adapter: ProtocolAdapter) -> None:
        """Register an adapter for a given protocol."""
        self._adapters[protocol] = adapter

    def get(self, protocol: ProtocolType) -> ProtocolAdapter:
        """Retrieve an adapter; raises KeyError if not registered."""
        if protocol not in self._adapters:
            raise KeyError(
                f"No adapter registered for protocol {protocol.value!r}. "
                f"Available: {[p.value for p in self._adapters]}"
            )
        return self._adapters[protocol]

    def supported_protocols(self) -> list[ProtocolType]:
        """Return list of registered protocol types."""
        return list(self._adapters.keys())


def _default_registry() -> AdapterRegistry:
    """Build and return a registry pre-populated with all built-in adapters."""
    from aumai_protocolbridge.adapters.a2a import A2AAdapter
    from aumai_protocolbridge.adapters.anthropic import AnthropicAdapter
    from aumai_protocolbridge.adapters.mcp import MCPAdapter
    from aumai_protocolbridge.adapters.openai import OpenAIAdapter

    registry = AdapterRegistry()
    registry.register(ProtocolType.openai, OpenAIAdapter())
    registry.register(ProtocolType.anthropic, AnthropicAdapter())
    registry.register(ProtocolType.mcp, MCPAdapter())
    registry.register(ProtocolType.a2a, A2AAdapter())
    return registry


class ProtocolBridge:
    """Translate tool definitions and messages between agent protocols."""

    def __init__(self, registry: AdapterRegistry | None = None) -> None:
        self._registry = registry or _default_registry()

    # ------------------------------------------------------------------
    # Tool definition translation
    # ------------------------------------------------------------------

    def translate_tool(
        self,
        tool_data: dict[str, Any],
        source: ProtocolType,
        target: ProtocolType,
    ) -> TranslationResult:
        """Translate a tool definition from source protocol to target protocol."""
        warnings: list[str] = []
        source_adapter = self._registry.get(source)
        target_adapter = self._registry.get(target)

        canonical = source_adapter.to_canonical(tool_data)

        if not canonical.name:
            warnings.append("Tool name is empty after parsing source format.")
        if not canonical.description:
            warnings.append("Tool description is empty — consider adding one.")

        translated = target_adapter.from_canonical(canonical)
        return TranslationResult(
            source_protocol=source,
            target_protocol=target,
            original=tool_data,
            translated=translated,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Message translation
    # ------------------------------------------------------------------

    def translate_message(
        self,
        msg: dict[str, Any],
        source: ProtocolType,
        target: ProtocolType,
    ) -> TranslationResult:
        """Translate a message dict between protocols.

        Uses adapter-specific message_to_canonical / message_from_canonical
        if available, otherwise falls back to a best-effort field mapping.
        """
        warnings: list[str] = []
        source_adapter = self._registry.get(source)
        target_adapter = self._registry.get(target)

        # Source: to canonical
        if hasattr(source_adapter, "message_to_canonical"):
            canonical_msg = source_adapter.message_to_canonical(msg)  # type: ignore[union-attr]
        else:
            canonical_msg = self._generic_message_to_canonical(msg)
            warnings.append(
                f"Adapter for {source.value} has no message_to_canonical; "
                "used generic fallback."
            )

        # Target: from canonical
        if hasattr(target_adapter, "message_from_canonical"):
            translated = target_adapter.message_from_canonical(canonical_msg)  # type: ignore[union-attr]
        else:
            translated = canonical_msg
            warnings.append(
                f"Adapter for {target.value} has no message_from_canonical; "
                "returned canonical form."
            )

        return TranslationResult(
            source_protocol=source,
            target_protocol=target,
            original=msg,
            translated=translated,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Tool call translation
    # ------------------------------------------------------------------

    def translate_tool_call(
        self,
        call: dict[str, Any],
        source: ProtocolType,
        target: ProtocolType,
    ) -> TranslationResult:
        """Translate a tool call dict between protocols."""
        warnings: list[str] = []
        source_adapter = self._registry.get(source)
        target_adapter = self._registry.get(target)

        # Source: to canonical call dict
        if hasattr(source_adapter, "tool_call_to_canonical"):
            canonical_call = source_adapter.tool_call_to_canonical(call)  # type: ignore[union-attr]
        elif hasattr(source_adapter, "task_call_to_canonical"):
            canonical_call = source_adapter.task_call_to_canonical(call)  # type: ignore[union-attr]
        else:
            canonical_call = call
            warnings.append(
                f"Adapter for {source.value} has no call deserializer; "
                "passed call through unchanged."
            )

        # Target: from canonical call dict
        if hasattr(target_adapter, "tool_call_from_canonical"):
            translated = target_adapter.tool_call_from_canonical(canonical_call)  # type: ignore[union-attr]
        elif hasattr(target_adapter, "task_call_from_canonical"):
            translated = target_adapter.task_call_from_canonical(canonical_call)  # type: ignore[union-attr]
        else:
            translated = canonical_call
            warnings.append(
                f"Adapter for {target.value} has no call serializer; "
                "returned canonical form."
            )

        return TranslationResult(
            source_protocol=source,
            target_protocol=target,
            original=call,
            translated=translated,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_tool(
        self, tool_data: dict[str, Any], protocol: ProtocolType
    ) -> list[str]:
        """Validate a tool definition against a protocol's expected structure.

        Returns a list of validation issues (empty = valid).
        """
        issues: list[str] = []
        adapter = self._registry.get(protocol)

        try:
            canonical = adapter.to_canonical(tool_data)
        except Exception as exc:
            issues.append(f"Parsing failed: {exc}")
            return issues

        if not canonical.name:
            issues.append("Missing required field: name")

        if protocol == ProtocolType.openai:
            if "type" not in tool_data and "type" not in tool_data.get(
                "function", {}
            ):
                issues.append(
                    "OpenAI tools should have type='function' wrapper "
                    "or bare function dict."
                )

        if protocol == ProtocolType.anthropic:
            if "input_schema" not in tool_data:
                issues.append(
                    "Anthropic tools require 'input_schema' field."
                )

        if protocol == ProtocolType.mcp:
            if "inputSchema" not in tool_data and "input_schema" not in tool_data:
                issues.append(
                    "MCP tools require 'inputSchema' field."
                )

        if protocol == ProtocolType.a2a:
            if "skill" not in tool_data and "name" not in tool_data:
                issues.append(
                    "A2A tools should have a 'skill' wrapper or bare skill dict."
                )

        return issues

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generic_message_to_canonical(msg: dict[str, Any]) -> dict[str, Any]:
        """Best-effort conversion of unknown message format to canonical dict."""
        return {
            "role": msg.get("role", "user"),
            "content": str(msg.get("content", "")),
            "tool_calls": None,
        }


__all__ = [
    "ProtocolAdapter",
    "AdapterRegistry",
    "ProtocolBridge",
]
