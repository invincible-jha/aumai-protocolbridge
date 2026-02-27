# Getting Started with aumai-protocolbridge

This guide walks you from installation to your first protocol translation in under five
minutes, then covers the common patterns needed for building multi-protocol agent systems.

---

## Prerequisites

- Python 3.11 or newer
- `pip` package manager
- Basic familiarity with at least one of: OpenAI function calling, Anthropic tool use,
  MCP (Model Context Protocol), or A2A (Agent-to-Agent protocol)

---

## Installation

### From PyPI (recommended)

```bash
pip install aumai-protocolbridge
```

Verify the installation:

```bash
protocolbridge --version
# aumai-protocolbridge, version 0.1.0

protocolbridge list-protocols
# Supported protocols:
#   openai
#   anthropic
#   mcp
#   a2a
```

### From source

```bash
git clone https://github.com/aumai/aumai-protocolbridge.git
cd aumai-protocolbridge
pip install .
```

### Developer mode

```bash
git clone https://github.com/aumai/aumai-protocolbridge.git
cd aumai-protocolbridge
pip install -e ".[dev]"
make test
```

---

## Your First Protocol Translation

This section translates an OpenAI-format tool definition into all three other formats.

### Step 1: Create a tool definition file

Save this as `weather_tool.json`:

```json
{
  "type": "function",
  "function": {
    "name": "get_current_weather",
    "description": "Retrieve current weather conditions for a given location",
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
          "description": "Temperature unit"
        }
      },
      "required": ["location"]
    }
  }
}
```

### Step 2: Translate to Anthropic format

```bash
protocolbridge translate \
  --source openai \
  --target anthropic \
  --input weather_tool.json
```

Output:

```json
{
  "name": "get_current_weather",
  "description": "Retrieve current weather conditions for a given location",
  "input_schema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City and country, e.g. 'London, UK'"
      },
      "unit": {
        "type": "string",
        "enum": ["celsius", "fahrenheit"],
        "description": "Temperature unit"
      }
    },
    "required": ["location"]
  }
}
```

Notice that OpenAI's `type: function` + `function:` wrapper is unwrapped, and the
`parameters` key becomes `input_schema`.

### Step 3: Translate to MCP format

```bash
protocolbridge translate \
  --source openai \
  --target mcp \
  --input weather_tool.json
```

### Step 4: Validate a tool definition

Before deploying a tool to a specific provider, validate that the structure is correct:

```bash
protocolbridge validate --protocol anthropic --input weather_tool.json
```

If the tool is valid: `Valid anthropic tool definition.`

If there is a structural issue, the command prints the problems and exits with code 1.

### Step 5: Save translated output to a file

```bash
protocolbridge translate \
  --source openai \
  --target mcp \
  --input weather_tool.json \
  --output weather_tool_mcp.json
```

---

## Common Patterns

### Pattern 1: Translate an entire directory of tool definitions

When migrating a library of tools from one provider to another:

```bash
mkdir -p anthropic_tools
for tool_file in openai_tools/*.json; do
  output_file="anthropic_tools/$(basename "$tool_file")"
  protocolbridge translate \
    --source openai \
    --target anthropic \
    --input "$tool_file" \
    --output "$output_file"
  echo "Translated $(basename "$tool_file")"
done
```

---

### Pattern 2: Python API — translate tools at runtime

This is the most common use case: your application receives tool definitions from one
provider and needs to pass them to another.

```python
from aumai_protocolbridge.core import ProtocolBridge
from aumai_protocolbridge.models import ProtocolType

bridge = ProtocolBridge()

def adapt_tools_for_provider(
    tools: list[dict],
    source: ProtocolType,
    target: ProtocolType,
) -> list[dict]:
    """Translate a list of tool definitions between protocols."""
    translated = []
    for tool in tools:
        result = bridge.translate_tool(tool, source=source, target=target)
        if result.warnings:
            for w in result.warnings:
                print(f"  Warning for {tool.get('name', '?')}: {w}")
        translated.append(result.translated)
    return translated

# Example: receive MCP tools and use them with an OpenAI client
mcp_tools = load_mcp_tool_manifest()  # your code
openai_tools = adapt_tools_for_provider(
    mcp_tools,
    source=ProtocolType.mcp,
    target=ProtocolType.openai,
)

from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather in London?"}],
    tools=openai_tools,
)
```

---

### Pattern 3: Validate tools before registering them

When building a tool registry that accepts contributions from multiple sources, validate
before accepting:

```python
from aumai_protocolbridge.core import ProtocolBridge
from aumai_protocolbridge.models import ProtocolType

bridge = ProtocolBridge()

def register_tool(tool_data: dict, claimed_protocol: ProtocolType) -> bool:
    """Validate a tool definition and register it if valid."""
    issues = bridge.validate_tool(tool_data, claimed_protocol)
    if issues:
        print(f"Rejected tool — {len(issues)} validation issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        return False

    # Tool is valid — translate to canonical and store
    adapter = bridge._registry.get(claimed_protocol)
    canonical = adapter.to_canonical(tool_data)
    print(f"Registered tool: {canonical.name}")
    return True


# Validate an Anthropic tool
anthropic_tool = {
    "name": "search_documents",
    "description": "Search internal documents",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
    }
}
register_tool(anthropic_tool, ProtocolType.anthropic)  # True
```

---

### Pattern 4: Writing a custom adapter

When you work with a protocol not in the built-in set:

```python
from typing import Any
from aumai_protocolbridge.core import AdapterRegistry, ProtocolBridge
from aumai_protocolbridge.models import ProtocolType, ToolDefinition


class LangChainToolAdapter:
    """Adapter for LangChain-style tool definitions."""

    def to_canonical(self, data: dict[str, Any]) -> ToolDefinition:
        """Parse a LangChain BaseTool dict to canonical form."""
        # LangChain tools have: name, description, args_schema (JSON schema)
        return ToolDefinition(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("args_schema", {}),
        )

    def from_canonical(self, tool: ToolDefinition) -> dict[str, Any]:
        """Render canonical ToolDefinition in LangChain format."""
        return {
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.parameters,
        }


# Build a bridge with the custom adapter registered
registry = AdapterRegistry()

# Register all built-in adapters
from aumai_protocolbridge.adapters.openai import OpenAIAdapter
from aumai_protocolbridge.adapters.anthropic import AnthropicAdapter
from aumai_protocolbridge.adapters.mcp import MCPAdapter
from aumai_protocolbridge.adapters.a2a import A2AAdapter

registry.register(ProtocolType.openai, OpenAIAdapter())
registry.register(ProtocolType.anthropic, AnthropicAdapter())
registry.register(ProtocolType.mcp, MCPAdapter())
registry.register(ProtocolType.a2a, A2AAdapter())

# Register the custom adapter (use a string value for ProtocolType)
# Note: for custom protocols, you can extend ProtocolType or use the registry directly
bridge = ProtocolBridge(registry=registry)
```

---

### Pattern 5: Translating messages in a multi-provider agent loop

In a multi-agent system where one agent uses Anthropic and another uses OpenAI:

```python
from aumai_protocolbridge.core import ProtocolBridge
from aumai_protocolbridge.models import ProtocolType

bridge = ProtocolBridge()

def route_message_to_provider(
    message: dict,
    source_protocol: ProtocolType,
    target_protocol: ProtocolType,
) -> dict:
    """Translate a message before sending to a different provider."""
    result = bridge.translate_message(
        msg=message,
        source=source_protocol,
        target=target_protocol,
    )
    for warning in result.warnings:
        print(f"Message translation warning: {warning}")
    return result.translated


# Anthropic agent sends a message → route to OpenAI agent
anthropic_response = {
    "role": "assistant",
    "content": "I need to search the web for that information."
}

openai_message = route_message_to_provider(
    anthropic_response,
    source_protocol=ProtocolType.anthropic,
    target_protocol=ProtocolType.openai,
)
```

---

## Troubleshooting FAQ

**Q: `protocolbridge translate` prints warnings to stderr. Should I be concerned?**

Warnings indicate that some information from the source format could not be represented
in the canonical form or the target format. The translation still succeeds. Common causes:

- Source adapter has no `message_to_canonical` method — uses generic fallback
- Tool has an empty name or description — usually a data quality issue in the source
- Target format does not support a field present in the source (e.g., `returns` schema
  in protocols that don't surface return types)

Warnings are written to stderr and can be captured or suppressed in scripts:
```bash
protocolbridge translate --source openai --target anthropic --input tool.json 2>/dev/null
```

---

**Q: `protocolbridge validate` says `Anthropic tools require 'input_schema' field` but my tool looks correct.**

Check that the key is exactly `input_schema` (with underscore), not `inputSchema`
(camelCase). Anthropic's format uses underscore; MCP uses camelCase `inputSchema`.

---

**Q: `KeyError: No adapter registered for protocol 'my_custom'`**

You are passing a `ProtocolType` value that has no registered adapter. The default
bridge only has adapters for `openai`, `anthropic`, `mcp`, and `a2a`. For custom
protocols, register an adapter as shown in Pattern 4 above.

---

**Q: The translated tool has an empty `description`.**

The source tool definition had no description. This is not an error — `description`
defaults to an empty string in `ToolDefinition`. The translation will include a warning:
`"Tool description is empty — consider adding one."` Add a description to the source
tool definition to eliminate this warning.

---

**Q: I need to translate a tool call response (the result), not the invocation.**

`ToolResult` is the canonical model for tool call responses. Use
`bridge.translate_tool_call()` with a dict that represents the response. Check whether
the adapter for your source protocol implements `tool_call_to_canonical` — if not, the
dict is passed through unchanged with a warning.

---

**Q: How do I check which adapters are loaded in my bridge instance?**

```python
bridge = ProtocolBridge()
supported = bridge._registry.supported_protocols()
print([p.value for p in supported])
# ['openai', 'anthropic', 'mcp', 'a2a']
```

---

**Q: Translation loses some fields from my OpenAI tool definition.**

The canonical `ToolDefinition` captures `name`, `description`, `parameters`, and
`returns`. Fields specific to OpenAI (like `strict: true` in structured outputs) have
no canonical equivalent and are dropped during `to_canonical()`. If you need to preserve
provider-specific fields, keep both the original and translated forms:

```python
result = bridge.translate_tool(tool, source=ProtocolType.openai, target=ProtocolType.mcp)
original = result.original       # untouched original dict
translated = result.translated   # translated dict
```
