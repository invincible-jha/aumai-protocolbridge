"""Tests for the CLI (aumai_protocolbridge.cli)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from aumai_protocolbridge.cli import main

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _write_json(tmp_path: Path, data: dict[str, Any], name: str = "input.json") -> Path:
    file = tmp_path / name
    file.write_text(json.dumps(data), encoding="utf-8")
    return file


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


class TestCLIVersion:
    """Tests for the --version flag."""

    def test_version_flag_reports_0_1_0(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


# ---------------------------------------------------------------------------
# list-protocols
# ---------------------------------------------------------------------------


class TestCLIListProtocols:
    """Tests for the list-protocols subcommand."""

    def test_all_four_protocols_shown(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["list-protocols"])
        assert result.exit_code == 0
        for proto in ("mcp", "a2a", "openai", "anthropic"):
            assert proto in result.output


# ---------------------------------------------------------------------------
# translate — tool
# ---------------------------------------------------------------------------


class TestCLITranslateTool:
    """Tests for the translate --type tool subcommand."""

    def test_openai_to_anthropic(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather info.",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            },
        }
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "openai",
                "--target", "anthropic",
                "--input", str(input_file),
                "--type", "tool",
            ],
        )
        assert result.exit_code == 0
        translated = json.loads(result.output)
        assert "input_schema" in translated
        assert translated["name"] == "get_weather"

    def test_anthropic_to_mcp(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {
            "name": "search",
            "description": "Search for something.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        }
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "anthropic",
                "--target", "mcp",
                "--input", str(input_file),
            ],
        )
        assert result.exit_code == 0
        translated = json.loads(result.output)
        assert "inputSchema" in translated

    def test_mcp_to_a2a(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {
            "name": "read_file",
            "description": "Read a file.",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        }
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "mcp",
                "--target", "a2a",
                "--input", str(input_file),
            ],
        )
        assert result.exit_code == 0
        translated = json.loads(result.output)
        assert "skill" in translated

    def test_output_written_to_file(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {
            "type": "function",
            "function": {"name": "fn", "description": "d", "parameters": {}},
        }
        input_file = _write_json(tmp_path, tool)
        output_file = tmp_path / "output.json"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "openai",
                "--target", "mcp",
                "--input", str(input_file),
                "--output", str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        translated = json.loads(output_file.read_text())
        assert "inputSchema" in translated

    def test_invalid_source_protocol_exits_nonzero(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {"name": "fn"}
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "not_a_protocol",
                "--target", "mcp",
                "--input", str(input_file),
            ],
        )
        assert result.exit_code != 0

    def test_warnings_printed_to_stderr(self, tmp_path: Path) -> None:
        # A tool with no name or description will trigger warnings.
        # Click's CliRunner captures stderr in result.output when mix_stderr is
        # the default (True). We check for "Warning" in the combined output.
        tool: dict[str, Any] = {
            "type": "function",
            "function": {"name": "", "description": "", "parameters": {}},
        }
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "openai",
                "--target", "mcp",
                "--input", str(input_file),
            ],
        )
        assert result.exit_code == 0
        assert "Warning" in result.output


# ---------------------------------------------------------------------------
# translate — message
# ---------------------------------------------------------------------------


class TestCLITranslateMessage:
    """Tests for the translate --type message subcommand."""

    def test_openai_message_to_anthropic(self, tmp_path: Path) -> None:
        msg: dict[str, Any] = {"role": "user", "content": "Hello from OpenAI"}
        input_file = _write_json(tmp_path, msg)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "openai",
                "--target", "anthropic",
                "--input", str(input_file),
                "--type", "message",
            ],
        )
        assert result.exit_code == 0
        translated = json.loads(result.output)
        assert translated["role"] == "user"

    def test_anthropic_message_to_openai(self, tmp_path: Path) -> None:
        msg: dict[str, Any] = {"role": "user", "content": "Hello from Anthropic"}
        input_file = _write_json(tmp_path, msg)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "anthropic",
                "--target", "openai",
                "--input", str(input_file),
                "--type", "message",
            ],
        )
        assert result.exit_code == 0
        translated = json.loads(result.output)
        assert translated["role"] == "user"


# ---------------------------------------------------------------------------
# translate — call
# ---------------------------------------------------------------------------


class TestCLITranslateCall:
    """Tests for the translate --type call subcommand."""

    def test_mcp_call_to_a2a(self, tmp_path: Path) -> None:
        call: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "fn", "arguments": {"x": 1}},
            "id": "c1",
        }
        input_file = _write_json(tmp_path, call)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "mcp",
                "--target", "a2a",
                "--input", str(input_file),
                "--type", "call",
            ],
        )
        assert result.exit_code == 0
        translated = json.loads(result.output)
        assert translated["skill_name"] == "fn"
        assert translated["task_id"] == "c1"

    def test_a2a_call_to_mcp(self, tmp_path: Path) -> None:
        call: dict[str, Any] = {
            "task_id": "t1",
            "skill_name": "run_job",
            "input": {"param": "value"},
        }
        input_file = _write_json(tmp_path, call)
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "translate",
                "--source", "a2a",
                "--target", "mcp",
                "--input", str(input_file),
                "--type", "call",
            ],
        )
        assert result.exit_code == 0
        translated = json.loads(result.output)
        assert translated["jsonrpc"] == "2.0"
        assert translated["params"]["name"] == "run_job"


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestCLIValidate:
    """Tests for the validate subcommand."""

    def test_valid_openai_tool_exits_zero(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {
            "type": "function",
            "function": {
                "name": "fn",
                "description": "d",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["validate", "--protocol", "openai", "--input", str(input_file)],
        )
        assert result.exit_code == 0
        assert "Valid" in result.output

    def test_valid_anthropic_tool_exits_zero(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {
            "name": "fn",
            "description": "d",
            "input_schema": {"type": "object", "properties": {}},
        }
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["validate", "--protocol", "anthropic", "--input", str(input_file)],
        )
        assert result.exit_code == 0

    def test_valid_mcp_tool_exits_zero(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {
            "name": "fn",
            "description": "d",
            "inputSchema": {"type": "object", "properties": {}},
        }
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["validate", "--protocol", "mcp", "--input", str(input_file)],
        )
        assert result.exit_code == 0

    def test_valid_a2a_tool_exits_zero(self, tmp_path: Path) -> None:
        tool: dict[str, Any] = {
            "skill": {
                "name": "fn",
                "description": "d",
                "parameters": {"type": "object"},
            }
        }
        input_file = _write_json(tmp_path, tool)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["validate", "--protocol", "a2a", "--input", str(input_file)],
        )
        assert result.exit_code == 0

    def test_invalid_anthropic_tool_exits_one(self, tmp_path: Path) -> None:
        # missing input_schema field
        bad: dict[str, Any] = {"name": "fn", "description": "d"}
        input_file = _write_json(tmp_path, bad)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["validate", "--protocol", "anthropic", "--input", str(input_file)],
        )
        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_invalid_mcp_tool_exits_one(self, tmp_path: Path) -> None:
        bad: dict[str, Any] = {"name": "fn", "description": "d"}
        input_file = _write_json(tmp_path, bad)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["validate", "--protocol", "mcp", "--input", str(input_file)],
        )
        assert result.exit_code == 1

    def test_invalid_protocol_value_exits_nonzero(self, tmp_path: Path) -> None:
        bad: dict[str, Any] = {"name": "fn"}
        input_file = _write_json(tmp_path, bad)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["validate", "--protocol", "grpc", "--input", str(input_file)],
        )
        assert result.exit_code != 0

    def test_missing_input_file_exits_nonzero(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                "--protocol", "openai",
                "--input", str(tmp_path / "does_not_exist.json"),
            ],
        )
        assert result.exit_code != 0
