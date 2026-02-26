"""CLI entry point for aumai-protocolbridge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from aumai_protocolbridge.models import ProtocolType


@click.group()
@click.version_option()
def main() -> None:
    """AumAI ProtocolBridge — translate between agent communication protocols."""


@main.command("translate")
@click.option(
    "--source",
    "source_protocol",
    required=True,
    type=click.Choice([p.value for p in ProtocolType]),
    help="Source protocol format.",
)
@click.option(
    "--target",
    "target_protocol",
    required=True,
    type=click.Choice([p.value for p in ProtocolType]),
    help="Target protocol format.",
)
@click.option(
    "--input",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON file containing the tool/message definition.",
)
@click.option(
    "--type",
    "translation_type",
    type=click.Choice(["tool", "message", "call"]),
    default="tool",
    show_default=True,
    help="Kind of object to translate.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write translated JSON to this file (default: stdout).",
)
def translate(
    source_protocol: str,
    target_protocol: str,
    input_file: Path,
    translation_type: str,
    output: Path | None,
) -> None:
    """Translate a tool definition, message, or tool call between protocols."""
    from aumai_protocolbridge.core import ProtocolBridge

    source = ProtocolType(source_protocol)
    target = ProtocolType(target_protocol)
    bridge = ProtocolBridge()

    data: dict[str, object] = json.loads(input_file.read_text(encoding="utf-8"))

    if translation_type == "tool":
        result = bridge.translate_tool(data, source, target)
    elif translation_type == "message":
        result = bridge.translate_message(data, source, target)
    else:
        result = bridge.translate_tool_call(data, source, target)

    for warning in result.warnings:
        click.echo(f"Warning: {warning}", err=True)

    output_json = json.dumps(result.translated, indent=2)
    if output:
        output.write_text(output_json, encoding="utf-8")
        click.echo(f"Translated output written to {output}")
    else:
        click.echo(output_json)


@main.command("validate")
@click.option(
    "--protocol",
    required=True,
    type=click.Choice([p.value for p in ProtocolType]),
    help="Protocol to validate against.",
)
@click.option(
    "--input",
    "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON file containing the tool definition.",
)
def validate(protocol: str, input_file: Path) -> None:
    """Validate a tool definition against a protocol's expected structure."""
    from aumai_protocolbridge.core import ProtocolBridge

    bridge = ProtocolBridge()
    proto = ProtocolType(protocol)
    data: dict[str, object] = json.loads(input_file.read_text(encoding="utf-8"))

    issues = bridge.validate_tool(data, proto)
    if issues:
        click.echo(f"Validation failed for protocol '{protocol}':")
        for issue in issues:
            click.echo(f"  - {issue}")
        sys.exit(1)
    else:
        click.echo(f"Valid {protocol} tool definition.")


@main.command("list-protocols")
def list_protocols() -> None:
    """List all supported agent protocols."""
    from aumai_protocolbridge.core import ProtocolBridge

    bridge = ProtocolBridge()
    supported = bridge._registry.supported_protocols()  # noqa: SLF001

    click.echo("Supported protocols:")
    for proto in supported:
        click.echo(f"  {proto.value}")


if __name__ == "__main__":
    main()
