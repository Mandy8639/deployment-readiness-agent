"""MCP server tests: list, call, and error paths."""

from deployment_readiness.mcp_server import handle


def _packet():
    return {
        "id": "DR-M01",
        "category": "clean",
        "customer": "Test Customer",
        "target_system": "SAP S/4HANA",
        "discovery_notes": [{"text": "Mapping confirmed.", "source": "w-1"}],
        "legacy_systems": [
            {
                "name": "SAP ECC 6.0",
                "module": "Finance",
                "records": 12000,
                "data_quality": "clean",
                "custom_code": "none",
            }
        ],
        "claims": [{"text": "Close improves 15%.", "source": "b-1"}],
        "required_evidence": ["SAP ECC 6.0"],
    }


def test_initialize_returns_protocol_version():
    response = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert response["result"]["protocolVersion"] == "2024-11-05"


def test_ping():
    response = handle({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert response["result"] == {}


def test_tools_list_exposes_three_allowlisted_tools():
    response = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}})
    names = [tool["name"] for tool in response["result"]["tools"]]
    assert names == [
        "read_deployment_packet",
        "analyze_fit_gap",
        "compile_cutover_checklist",
    ]


def test_tools_call_read_packet():
    response = handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "read_deployment_packet", "arguments": {"packet": _packet()}},
        }
    )
    assert "DR-M01" in response["result"]["content"][0]["text"]


def test_tools_call_fit_gap():
    response = handle(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "analyze_fit_gap", "arguments": {"packet": _packet()}},
        }
    )
    assert "clean" in response["result"]["content"][0]["text"]


def test_tools_call_checklist():
    response = handle(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "compile_cutover_checklist",
                "arguments": {"packet": _packet(), "decision": "GO"},
            },
        }
    )
    assert "GO" in response["result"]["content"][0]["text"]


def test_unknown_tool_returns_error():
    response = handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "delete_everything", "arguments": {}},
        }
    )
    assert "error" in response


def test_notification_returns_none():
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
