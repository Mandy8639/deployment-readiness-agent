"""Minimal MCP server (stdio JSON-RPC 2.0), no external dependencies.

Exposes the three allowlisted tools over the Model Context Protocol:
tools/list and tools/call. Run: python -m deployment_readiness.mcp_server
"""

from __future__ import annotations

import json
import sys

from deployment_readiness.packet import packet_to_dict
from deployment_readiness.tools import (
    ALLOWED_TOOLS,
    analyze_fit_gap,
    compile_cutover_checklist,
    read_deployment_packet,
)

TOOLS = {
    "read_deployment_packet": {
        "description": "Load and validate a deployment packet.",
        "inputSchema": {
            "type": "object",
            "properties": {"packet": {"type": "object"}},
            "required": ["packet"],
        },
    },
    "analyze_fit_gap": {
        "description": "Per-system fit-gap status from a deployment packet.",
        "inputSchema": {
            "type": "object",
            "properties": {"packet": {"type": "object"}},
            "required": ["packet"],
        },
    },
    "compile_cutover_checklist": {
        "description": "Cutover-readiness checklist and go/no-go verdict.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "packet": {"type": "object"},
                "decision": {"type": "string"},
            },
            "required": ["packet", "decision"],
        },
    },
}


def _tool_result(payload: object) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]}


def handle(request: dict) -> dict | None:
    """Handle one JSON-RPC request. Returns None for notifications."""
    method = request.get("method", "")
    request_id = request.get("id")
    params = request.get("params", {}) or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "deployment-readiness-agent", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {"name": name, **spec} for name, spec in TOOLS.items() if name in ALLOWED_TOOLS
                ]
            },
        }
    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}
        try:
            if name == "read_deployment_packet":
                packet = read_deployment_packet(arguments["packet"])
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": _tool_result(packet_to_dict(packet)),
                }
            if name == "analyze_fit_gap":
                packet = read_deployment_packet(arguments["packet"])
                items = analyze_fit_gap(packet)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": _tool_result([item.__dict__ for item in items]),
                }
            if name == "compile_cutover_checklist":
                packet = read_deployment_packet(arguments["packet"])
                items = analyze_fit_gap(packet)
                entries, verdict = compile_cutover_checklist(packet, items, arguments["decision"])
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": _tool_result(
                        {"verdict": verdict, "entries": [e.__dict__ for e in entries]}
                    ),
                }
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": f"unknown tool: {name}"},
            }
        except (KeyError, ValueError) as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": str(exc)},
            }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"unknown method: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
