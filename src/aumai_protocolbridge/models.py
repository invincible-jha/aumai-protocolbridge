"""Pydantic models for aumai-protocolbridge."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProtocolType(str, Enum):
    """Supported agent communication protocols."""

    mcp = "mcp"
    a2a = "a2a"
    openai = "openai"
    anthropic = "anthropic"


class ToolDefinition(BaseModel):
    """Protocol-agnostic canonical tool definition."""

    name: str = Field(..., description="Tool name (snake_case preferred)")
    description: str = Field(default="", description="Human-readable description")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema object describing input parameters",
    )
    returns: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema object describing the return value",
    )


class ToolCall(BaseModel):
    """Represents a call to a tool (protocol-agnostic)."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str


class ToolResult(BaseModel):
    """Represents the result of a tool call."""

    call_id: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Message(BaseModel):
    """A protocol-agnostic message in an agent conversation."""

    role: str = Field(..., description="Message role: user, assistant, tool, system")
    content: str = Field(default="")
    tool_calls: list[ToolCall] | None = None


class TranslationResult(BaseModel):
    """Result of a protocol translation operation."""

    source_protocol: ProtocolType
    target_protocol: ProtocolType
    original: dict[str, Any]
    translated: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


__all__ = [
    "ProtocolType",
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "Message",
    "TranslationResult",
]
