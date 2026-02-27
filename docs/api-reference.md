# API Reference — aumai-protocolbridge

Complete reference for all public classes, functions, and models in
`aumai-protocolbridge`.

---

## Module: `aumai_protocolbridge.models`

Pydantic data models providing the canonical protocol-agnostic representation used
throughout the library.

---

### `ProtocolType`

```python
class ProtocolType(str, Enum):
```

Supported agent communication protocols.

**Values:**

| Value | String | Description |
|---|---|---|
| `ProtocolType.mcp` | `"mcp"` | Model Context Protocol |
| `ProtocolType.a2a` | `"a2a"` | Agent-to-Agent protocol |
| `ProtocolType.openai` | `"openai"` | OpenAI function calling format |
| `ProtocolType.anthropic` | `"anthropic"` | Anthropic tool use format |

Being a `str` Enum, values can be compared to strings and serialize as strings in JSON.

---

### `ToolDefinition`

```python
class ToolDefinition(BaseModel):
```

Protocol-agnostic canonical representation of a tool definition. This is the hub of all
translation operations — all protocols translate to and from this form.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | Yes | Tool name. Snake_case preferred. This is the callable identifier. |
| `description` | `str` | No | Human-readable description of what the tool does. Defaults to `""`. |
| `parameters` | `dict[str, Any]` | No | JSON Schema `object` describing the tool's input parameters. Defaults to `{}`. |
| `returns` | `dict[str, Any]` | No | JSON Schema `object` describing the return value. Defaults to `{}`. Not all protocols expose this field. |

**Example:**

```python
from aumai_protocolbridge.models import ToolDefinition

tool = ToolDefinition(
    name="search_documents",
    description="Search internal document store by keyword query",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 10
            }
        },
        "required": ["query"]
    },
    returns={
        "type": "array",
        "items": {"type": "object"}
    }
)
```

---

### `ToolCall`

```python
class ToolCall(BaseModel):
```

Protocol-agnostic representation of a tool call invocation — when an agent calls a tool
with specific arguments.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `tool_name` | `str` | Yes | Name of the tool being called. |
| `arguments` | `dict[str, Any]` | No | Arguments to pass to the tool. Defaults to `{}`. |
| `call_id` | `str` | Yes | Unique identifier for this call invocation. Used to match calls to results. |

**Example:**

```python
from aumai_protocolbridge.models import ToolCall

call = ToolCall(
    tool_name="search_documents",
    arguments={"query": "quarterly revenue", "max_results": 5},
    call_id="call_abc123",
)
```

---

### `ToolResult`

```python
class ToolResult(BaseModel):
```

Protocol-agnostic representation of a tool call result.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `call_id` | `str` | Yes | Must match the `call_id` of the corresponding `ToolCall`. |
| `result` | `dict[str, Any]` | No | The tool's return value. Defaults to `{}`. |
| `error` | `str \| None` | No | Error message if the tool call failed. `None` on success. Defaults to `None`. |

**Example:**

```python
from aumai_protocolbridge.models import ToolResult

# Successful result
result = ToolResult(
    call_id="call_abc123",
    result={"documents": [{"id": "doc1", "content": "..."}]},
    error=None,
)

# Error result
error_result = ToolResult(
    call_id="call_abc123",
    result={},
    error="Tool timed out after 30 seconds",
)
```

---

### `Message`

```python
class Message(BaseModel):
```

Protocol-agnostic message in an agent conversation.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `role` | `str` | Yes | Message role. One of: `"user"`, `"assistant"`, `"tool"`, `"system"`. |
| `content` | `str` | No | Text content of the message. Defaults to `""`. |
| `tool_calls` | `list[ToolCall] \| None` | No | Tool calls made in this message. `None` if no tool calls. Defaults to `None`. |

**Example:**

```python
from aumai_protocolbridge.models import Message, ToolCall

# Simple user message
msg = Message(role="user", content="What is the weather in Tokyo?")

# Assistant message with a tool call
assistant_msg = Message(
    role="assistant",
    content="",
    tool_calls=[
        ToolCall(
            tool_name="get_weather",
            arguments={"location": "Tokyo"},
            call_id="call_xyz"
        )
    ]
)
```

---

### `TranslationResult`

```python
class TranslationResult(BaseModel):
```

The result of a protocol translation operation. Contains both the original and
translated forms, plus any warnings about information loss.

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `source_protocol` | `ProtocolType` | Yes | The protocol of the input. |
| `target_protocol` | `ProtocolType` | Yes | The protocol of the output. |
| `original` | `dict[str, Any]` | Yes | The unmodified input dict. |
| `translated` | `dict[str, Any]` | Yes | The translated output dict in the target format. |
| `warnings` | `list[str]` | No | Non-fatal warnings about the translation. Empty list if none. Defaults to `[]`. |

Warnings are generated when:
- The tool name is empty after parsing
- The tool description is empty
- An adapter falls back to generic message handling
- A call adapter is missing and the dict is passed through unchanged

**Example:**

```python
result = bridge.translate_tool(tool_data, ProtocolType.openai, ProtocolType.mcp)

print(f"Translated from {result.source_protocol.value} to {result.target_protocol.value}")
if result.warnings:
    print("Warnings:")
    for w in result.warnings:
        print(f"  - {w}")

# Use the translated output
send_to_mcp_server(result.translated)
```

---

## Module: `aumai_protocolbridge.core`

The main operational classes for protocol translation.

---

### `ProtocolAdapter` (Protocol)

```python
@runtime_checkable
class ProtocolAdapter(Protocol):
```

Structural interface that all adapter implementations must satisfy. Uses Python's
`typing.Protocol` with `@runtime_checkable`, meaning any class that implements the
required methods satisfies this interface without explicit inheritance.

**Required methods:**

#### `to_canonical(data: dict[str, Any]) -> ToolDefinition`

Convert a protocol-specific tool dict to the canonical `ToolDefinition`.

**Parameters:**
- `data` (`dict[str, Any]`) — Protocol-specific tool definition dict.

**Returns:** `ToolDefinition`

---

#### `from_canonical(tool: ToolDefinition) -> dict[str, Any]`

Convert a canonical `ToolDefinition` to the protocol-specific format.

**Parameters:**
- `tool` (`ToolDefinition`)

**Returns:** `dict[str, Any]` — Protocol-specific dict.

**Checking conformance at runtime:**

```python
from aumai_protocolbridge.core import ProtocolAdapter

adapter = MyCustomAdapter()
assert isinstance(adapter, ProtocolAdapter)  # True if both methods exist
```

---

### `AdapterRegistry`

```python
class AdapterRegistry:
```

Registry that maps `ProtocolType` enum values to adapter instances.

**Constructor:**

```python
AdapterRegistry()
```

Starts empty. Use `register()` to add adapters.

---

#### `register(protocol: ProtocolType, adapter: ProtocolAdapter) -> None`

Register an adapter for a given protocol. Overwrites any existing registration.

**Parameters:**
- `protocol` (`ProtocolType`) — The protocol this adapter handles.
- `adapter` (`ProtocolAdapter`) — An object satisfying the `ProtocolAdapter` protocol.

---

#### `get(protocol: ProtocolType) -> ProtocolAdapter`

Retrieve the adapter for a given protocol.

**Parameters:**
- `protocol` (`ProtocolType`)

**Returns:** `ProtocolAdapter`

**Raises:** `KeyError` — If no adapter is registered for the given protocol. The error
message lists all currently registered protocols.

---

#### `supported_protocols() -> list[ProtocolType]`

Return a list of all registered protocol types.

**Returns:** `list[ProtocolType]`

**Example:**

```python
from aumai_protocolbridge.core import AdapterRegistry
from aumai_protocolbridge.models import ProtocolType
from aumai_protocolbridge.adapters.openai import OpenAIAdapter

registry = AdapterRegistry()
registry.register(ProtocolType.openai, OpenAIAdapter())
print(registry.supported_protocols())  # [ProtocolType.openai]
```

---

### `ProtocolBridge`

```python
class ProtocolBridge:
```

The main entry point for all protocol translation and validation operations.

**Constructor:**

```python
ProtocolBridge(registry: AdapterRegistry | None = None)
```

**Parameters:**
- `registry` (`AdapterRegistry | None`) — Custom adapter registry. If `None`, the
  default registry is used, which pre-populates adapters for `openai`, `anthropic`,
  `mcp`, and `a2a`.

**Example:**

```python
from aumai_protocolbridge.core import ProtocolBridge

# Default bridge with all built-in adapters
bridge = ProtocolBridge()

# Bridge with a custom registry
from aumai_protocolbridge.core import AdapterRegistry
custom_registry = AdapterRegistry()
# ... register your adapters ...
bridge = ProtocolBridge(registry=custom_registry)
```

---

#### `translate_tool(tool_data: dict[str, Any], source: ProtocolType, target: ProtocolType) -> TranslationResult`

Translate a tool definition from source protocol to target protocol.

Translation path: `source_adapter.to_canonical(tool_data)` → `ToolDefinition` →
`target_adapter.from_canonical(canonical)`.

**Parameters:**
- `tool_data` (`dict[str, Any]`) — Protocol-specific tool definition in the source
  format.
- `source` (`ProtocolType`) — The source protocol.
- `target` (`ProtocolType`) — The target protocol.

**Returns:** `TranslationResult`

**Raises:** `KeyError` if either `source` or `target` protocol has no registered adapter.

Warnings are added to `result.warnings` when:
- `canonical.name` is empty after parsing
- `canonical.description` is empty

**Example:**

```python
openai_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}
    }
}

result = bridge.translate_tool(
    tool_data=openai_tool,
    source=ProtocolType.openai,
    target=ProtocolType.anthropic,
)
print(result.translated)
# {"name": "get_weather", "description": "...", "input_schema": {...}}
```

---

#### `translate_message(msg: dict[str, Any], source: ProtocolType, target: ProtocolType) -> TranslationResult`

Translate a message dict between protocols.

If the source adapter implements `message_to_canonical()`, it is used. Otherwise, the
generic fallback `_generic_message_to_canonical()` is used, and a warning is added. The
same applies to the target adapter's `message_from_canonical()`.

**Parameters:**
- `msg` (`dict[str, Any]`) — Protocol-specific message dict.
- `source` (`ProtocolType`)
- `target` (`ProtocolType`)

**Returns:** `TranslationResult`

**Generic fallback behavior:** Maps `msg.get("role", "user")` and
`str(msg.get("content", ""))` into a canonical dict. `tool_calls` is set to `None`.

---

#### `translate_tool_call(call: dict[str, Any], source: ProtocolType, target: ProtocolType) -> TranslationResult`

Translate a tool call invocation dict between protocols.

Checks for the following methods on adapters in order:
- Source: `tool_call_to_canonical` (OpenAI-style), then `task_call_to_canonical`
  (A2A-style), then passes through unchanged with a warning.
- Target: `tool_call_from_canonical`, then `task_call_from_canonical`, then returns
  canonical dict unchanged with a warning.

**Parameters:**
- `call` (`dict[str, Any]`) — Protocol-specific tool call dict.
- `source` (`ProtocolType`)
- `target` (`ProtocolType`)

**Returns:** `TranslationResult`

---

#### `validate_tool(tool_data: dict[str, Any], protocol: ProtocolType) -> list[str]`

Validate a tool definition against a protocol's expected structural requirements.

**Parameters:**
- `tool_data` (`dict[str, Any]`) — Tool definition to validate.
- `protocol` (`ProtocolType`) — Protocol to validate against.

**Returns:** `list[str]` — List of validation issue strings. Empty list means the tool
is valid.

**Protocol-specific checks:**

| Protocol | Checks |
|---|---|
| `openai` | Warns if no `type='function'` wrapper or bare function dict |
| `anthropic` | Requires `input_schema` field |
| `mcp` | Requires `inputSchema` or `input_schema` field |
| `a2a` | Requires `skill` wrapper or bare dict with `name` |
| All | Parses with `to_canonical()` — raises a parsing failure issue if it throws |
| All | Checks that `name` is not empty after parsing |

**Example:**

```python
issues = bridge.validate_tool({"name": "my_tool"}, ProtocolType.anthropic)
# ["Anthropic tools require 'input_schema' field."]

issues = bridge.validate_tool(
    {"name": "my_tool", "description": "does stuff",
     "input_schema": {"type": "object"}},
    ProtocolType.anthropic
)
# []  (valid)
```

---

## Module: `aumai_protocolbridge` (top-level)

The package `__init__.py` re-exports all six models for convenient top-level import.

```python
from aumai_protocolbridge import (
    Message,
    ProtocolType,
    ToolCall,
    ToolDefinition,
    ToolResult,
    TranslationResult,
)
```

**`__version__`** (`str`) — Package version string, e.g. `"0.1.0"`.

---

## Module: `aumai_protocolbridge.adapters`

Built-in protocol adapters. Each adapter is in its own submodule.

### `aumai_protocolbridge.adapters.openai.OpenAIAdapter`

Handles OpenAI function calling format.

**`to_canonical(data)`**: Unwraps `{"type": "function", "function": {...}}` or bare
function dict. Maps `parameters` → `ToolDefinition.parameters`.

**`from_canonical(tool)`**: Wraps in `{"type": "function", "function": {"name": ...,
"description": ..., "parameters": ...}}`.

**Additional methods** (used by `translate_message` and `translate_tool_call`):
- `message_to_canonical(msg)` — handles `tool_calls` array
- `message_from_canonical(canonical)` — produces OpenAI-format message
- `tool_call_to_canonical(call)` — handles `{"id": ..., "function": {"name": ...,
  "arguments": ...}}`
- `tool_call_from_canonical(call)` — produces OpenAI-format tool call

---

### `aumai_protocolbridge.adapters.anthropic.AnthropicAdapter`

Handles Anthropic tool use format.

**`to_canonical(data)`**: Maps `input_schema` → `ToolDefinition.parameters`.

**`from_canonical(tool)`**: Produces `{"name": ..., "description": ...,
"input_schema": ...}`.

---

### `aumai_protocolbridge.adapters.mcp.MCPAdapter`

Handles Model Context Protocol format.

**`to_canonical(data)`**: Maps `inputSchema` (camelCase) or `input_schema` →
`ToolDefinition.parameters`.

**`from_canonical(tool)`**: Produces `{"name": ..., "description": ...,
"inputSchema": ...}`.

---

### `aumai_protocolbridge.adapters.a2a.A2AAdapter`

Handles Agent-to-Agent protocol format.

**`to_canonical(data)`**: Unwraps `{"skill": {...}}` wrapper or bare skill dict. Maps
skill fields to `ToolDefinition`.

**`from_canonical(tool)`**: Produces `{"skill": {"name": ..., "description": ...,
"parameters": ...}}`.
