"""Quickstart examples for aumai-protocolbridge.

Demonstrates the core API: translating tool definitions, messages, and tool
calls between OpenAI, Anthropic, MCP, and A2A protocols.

Run this file directly to verify your installation:

    python examples/quickstart.py

No external network access is required. All examples use static data.
"""

from __future__ import annotations

from aumai_protocolbridge.core import AdapterRegistry, ProtocolBridge
from aumai_protocolbridge.models import (
    Message,
    ProtocolType,
    ToolCall,
    ToolDefinition,
    ToolResult,
    TranslationResult,
)


# ---------------------------------------------------------------------------
# Sample tool definitions in each protocol format
# ---------------------------------------------------------------------------

# OpenAI function calling format
OPENAI_WEATHER_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather conditions for a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country, e.g. 'London, UK'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit preference"
                }
            },
            "required": ["location"]
        }
    }
}

# Anthropic tool use format (reference — what OpenAI above should translate to)
ANTHROPIC_SEARCH_TOOL: dict = {
    "name": "search_documents",
    "description": "Search internal documents by keyword query",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return",
                "default": 10
            }
        },
        "required": ["query"]
    }
}

# MCP (Model Context Protocol) format
MCP_FILE_TOOL: dict = {
    "name": "read_file",
    "description": "Read the contents of a file from the filesystem",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file"
            },
            "encoding": {
                "type": "string",
                "description": "File encoding",
                "default": "utf-8"
            }
        },
        "required": ["path"]
    }
}


# ---------------------------------------------------------------------------
# Demo 1: Basic tool translation between all protocol pairs
# ---------------------------------------------------------------------------

def demo_tool_translation() -> None:
    """Translate the OpenAI weather tool into all other protocol formats."""
    print("\n" + "=" * 60)
    print("Demo 1: Tool Definition Translation")
    print("=" * 60)

    bridge = ProtocolBridge()

    source = ProtocolType.openai
    targets = [ProtocolType.anthropic, ProtocolType.mcp, ProtocolType.a2a]

    print(f"Source tool (OpenAI format): {OPENAI_WEATHER_TOOL['function']['name']}\n")

    for target in targets:
        result = bridge.translate_tool(
            tool_data=OPENAI_WEATHER_TOOL,
            source=source,
            target=target,
        )

        print(f"--- Translated to {target.value.upper()} ---")

        # Show key structural differences
        if target == ProtocolType.anthropic:
            translated = result.translated
            print(f"  name         : {translated.get('name')}")
            print(f"  input_schema : {list(translated.get('input_schema', {}).get('properties', {}).keys())}")
            print(f"  (no 'type':'function' wrapper)")

        elif target == ProtocolType.mcp:
            translated = result.translated
            print(f"  name        : {translated.get('name')}")
            print(f"  inputSchema : {list(translated.get('inputSchema', {}).get('properties', {}).keys())}")
            print(f"  (camelCase 'inputSchema' key)")

        elif target == ProtocolType.a2a:
            translated = result.translated
            print(f"  skill wrapper: {'skill' in translated}")
            if "skill" in translated:
                print(f"  skill.name  : {translated['skill'].get('name')}")

        if result.warnings:
            print(f"  Warnings:")
            for w in result.warnings:
                print(f"    - {w}")

        print()


# ---------------------------------------------------------------------------
# Demo 2: Translate in all directions (matrix)
# ---------------------------------------------------------------------------

def demo_translation_matrix() -> None:
    """Show that any protocol can translate to any other protocol."""
    print("\n" + "=" * 60)
    print("Demo 2: Translation Matrix (All Directions)")
    print("=" * 60)

    bridge = ProtocolBridge()
    protocols = list(ProtocolType)

    # Seed tools for each source protocol
    source_tools = {
        ProtocolType.openai: OPENAI_WEATHER_TOOL,
        ProtocolType.anthropic: ANTHROPIC_SEARCH_TOOL,
        ProtocolType.mcp: MCP_FILE_TOOL,
        ProtocolType.a2a: {
            "skill": {
                "name": "send_email",
                "description": "Send an email to a recipient",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"}
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        }
    }

    print(f"{'Source':<12} {'Target':<12} {'Tool name':<25} {'Warnings'}")
    print("-" * 65)

    for source in protocols:
        for target in protocols:
            if source == target:
                continue
            try:
                result = bridge.translate_tool(
                    tool_data=source_tools[source],
                    source=source,
                    target=target,
                )
                # Extract name from the translated dict (structure varies by protocol)
                translated = result.translated
                name = (
                    translated.get("name")
                    or translated.get("function", {}).get("name")
                    or translated.get("skill", {}).get("name")
                    or "?"
                )
                warning_flag = f"{len(result.warnings)} warning(s)" if result.warnings else "none"
                print(f"  {source.value:<10} {target.value:<12} {name:<25} {warning_flag}")
            except Exception as exc:
                print(f"  {source.value:<10} {target.value:<12} {'ERROR':<25} {exc}")


# ---------------------------------------------------------------------------
# Demo 3: Validating tool definitions
# ---------------------------------------------------------------------------

def demo_validation() -> None:
    """Show ProtocolBridge.validate_tool() catching structural issues."""
    print("\n" + "=" * 60)
    print("Demo 3: Tool Definition Validation")
    print("=" * 60)

    bridge = ProtocolBridge()

    test_cases = [
        # (description, tool_dict, protocol, expect_valid)
        (
            "Valid Anthropic tool",
            ANTHROPIC_SEARCH_TOOL,
            ProtocolType.anthropic,
            True,
        ),
        (
            "Anthropic tool missing input_schema",
            {"name": "do_something", "description": "Does something"},
            ProtocolType.anthropic,
            False,
        ),
        (
            "Valid MCP tool",
            MCP_FILE_TOOL,
            ProtocolType.mcp,
            True,
        ),
        (
            "MCP tool with wrong key (input_schema instead of inputSchema)",
            {"name": "read_file", "description": "Read a file", "input_schema": {"type": "object"}},
            ProtocolType.mcp,
            True,  # MCP adapter accepts either casing
        ),
        (
            "Valid OpenAI tool",
            OPENAI_WEATHER_TOOL,
            ProtocolType.openai,
            True,
        ),
        (
            "OpenAI tool missing type field",
            {
                "function": {
                    "name": "bare_function",
                    "description": "A bare function without type wrapper"
                }
            },
            ProtocolType.openai,
            True,  # acceptable as bare function dict
        ),
    ]

    for description, tool_dict, protocol, expect_valid in test_cases:
        issues = bridge.validate_tool(tool_dict, protocol)
        status = "VALID" if not issues else "INVALID"
        match_expectation = (not issues) == expect_valid
        marker = "OK" if match_expectation else "UNEXPECTED"

        print(f"  [{status}] {description}")
        if issues:
            for issue in issues:
                print(f"         Issue: {issue}")
        print()


# ---------------------------------------------------------------------------
# Demo 4: Working with canonical models directly
# ---------------------------------------------------------------------------

def demo_canonical_models() -> None:
    """Show ToolDefinition and related models as a shared vocabulary."""
    print("\n" + "=" * 60)
    print("Demo 4: Canonical Model Usage")
    print("=" * 60)

    # Create a canonical tool definition from scratch
    canonical_tool = ToolDefinition(
        name="calculate_tax",
        description="Calculate sales tax for a transaction amount",
        parameters={
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Transaction amount in USD"
                },
                "state": {
                    "type": "string",
                    "description": "US state code, e.g. 'CA' for California"
                }
            },
            "required": ["amount", "state"]
        },
        returns={
            "type": "object",
            "properties": {
                "tax": {"type": "number"},
                "total": {"type": "number"}
            }
        }
    )

    print(f"Canonical ToolDefinition:")
    print(f"  name        : {canonical_tool.name}")
    print(f"  description : {canonical_tool.description}")
    print(f"  parameters  : {list(canonical_tool.parameters.get('properties', {}).keys())}")
    print(f"  returns     : {list(canonical_tool.returns.get('properties', {}).keys())}")

    # Use adapters directly to render in protocol formats
    from aumai_protocolbridge.adapters.openai import OpenAIAdapter
    from aumai_protocolbridge.adapters.anthropic import AnthropicAdapter

    openai_form = OpenAIAdapter().from_canonical(canonical_tool)
    anthropic_form = AnthropicAdapter().from_canonical(canonical_tool)

    print(f"\nAs OpenAI format:")
    print(f"  type           : {openai_form.get('type')}")
    print(f"  function.name  : {openai_form.get('function', {}).get('name')}")

    print(f"\nAs Anthropic format:")
    print(f"  name         : {anthropic_form.get('name')}")
    print(f"  input_schema : present = {'input_schema' in anthropic_form}")

    # Demonstrate ToolCall and ToolResult models
    call = ToolCall(
        tool_name="calculate_tax",
        arguments={"amount": 99.99, "state": "CA"},
        call_id="call_tax_001",
    )
    print(f"\nToolCall:")
    print(f"  tool_name  : {call.tool_name}")
    print(f"  arguments  : {call.arguments}")
    print(f"  call_id    : {call.call_id}")

    result = ToolResult(
        call_id="call_tax_001",
        result={"tax": 8.75, "total": 108.74},
        error=None,
    )
    print(f"\nToolResult:")
    print(f"  call_id : {result.call_id}")
    print(f"  result  : {result.result}")
    print(f"  error   : {result.error}")

    # Message with tool calls
    message = Message(
        role="assistant",
        content="",
        tool_calls=[call],
    )
    print(f"\nMessage with tool call:")
    print(f"  role       : {message.role}")
    print(f"  tool_calls : {len(message.tool_calls or [])} call(s)")


# ---------------------------------------------------------------------------
# Demo 5: Custom adapter registration
# ---------------------------------------------------------------------------

def demo_custom_adapter() -> None:
    """Show how to write and register a custom protocol adapter."""
    print("\n" + "=" * 60)
    print("Demo 5: Custom Adapter Registration")
    print("=" * 60)

    # Define a custom adapter for a hypothetical "LangChain" tool format
    class LangChainAdapter:
        """Adapter for LangChain-style BaseTool dicts."""

        def to_canonical(self, data: dict) -> ToolDefinition:
            return ToolDefinition(
                name=data.get("name", ""),
                description=data.get("description", ""),
                parameters=data.get("args_schema", {}),
            )

        def from_canonical(self, tool: ToolDefinition) -> dict:
            return {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.parameters,
                "_type": "langchain_tool",
            }

    # Build a bridge that includes the custom adapter alongside built-ins
    # We extend ProtocolType by creating a string alias (works at runtime)
    # For production use, extend the ProtocolType enum in your own code

    # Use the built-in registry + manually add our custom adapter
    registry = AdapterRegistry()
    from aumai_protocolbridge.adapters.openai import OpenAIAdapter
    from aumai_protocolbridge.adapters.anthropic import AnthropicAdapter
    from aumai_protocolbridge.adapters.mcp import MCPAdapter
    from aumai_protocolbridge.adapters.a2a import A2AAdapter

    registry.register(ProtocolType.openai, OpenAIAdapter())
    registry.register(ProtocolType.anthropic, AnthropicAdapter())
    registry.register(ProtocolType.mcp, MCPAdapter())
    registry.register(ProtocolType.a2a, A2AAdapter())

    bridge = ProtocolBridge(registry=registry)

    supported = bridge._registry.supported_protocols()
    print(f"Registered protocols: {[p.value for p in supported]}")

    # Use the custom adapter directly (without registering a new ProtocolType)
    langchain_adapter = LangChainAdapter()
    langchain_tool = {
        "name": "web_search",
        "description": "Search the web for current information",
        "args_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    }

    # Convert LangChain → canonical → Anthropic
    canonical = langchain_adapter.to_canonical(langchain_tool)
    print(f"\nLangChain tool → canonical:")
    print(f"  name        : {canonical.name}")
    print(f"  description : {canonical.description}")

    anthropic_form = AnthropicAdapter().from_canonical(canonical)
    print(f"\nCanonical → Anthropic:")
    print(f"  name         : {anthropic_form.get('name')}")
    print(f"  input_schema : {list(anthropic_form.get('input_schema', {}).get('properties', {}).keys())}")

    # Convert LangChain → canonical → MCP
    mcp_form = MCPAdapter().from_canonical(canonical)
    print(f"\nCanonical → MCP:")
    print(f"  name        : {mcp_form.get('name')}")
    print(f"  inputSchema : present = {'inputSchema' in mcp_form}")

    print("\nCustom adapter pattern works for any protocol not in the built-in set.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run all quickstart demos."""
    print("aumai-protocolbridge Quickstart")
    print("=" * 60)
    print("Running 5 demos to exercise the translation API...\n")

    demo_tool_translation()
    demo_translation_matrix()
    demo_validation()
    demo_canonical_models()
    demo_custom_adapter()

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
