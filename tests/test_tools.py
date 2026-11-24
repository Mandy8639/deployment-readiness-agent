"""Tool tests: packet validation, fit-gap statuses, checklist verdicts."""

import pytest

from deployment_readiness.packet import packet_from_dict
from deployment_readiness.tools import (
    analyze_fit_gap,
    compile_cutover_checklist,
    read_deployment_packet,
)


def _packet(**overrides):
    packet = {
        "id": "DR-T01",
        "category": "clean",
        "customer": "Test Customer",
        "target_system": "SAP S/4HANA",
        "discovery_notes": [],
        "legacy_systems": [],
        "claims": [],
        "required_evidence": [],
    }
    packet.update(overrides)
    return packet


def _system(**overrides):
    system = {
        "name": "SAP ECC 6.0",
        "module": "Finance",
        "records": 12000,
        "data_quality": "clean",
        "custom_code": "none",
    }
    system.update(overrides)
    return system


def test_read_packet_requires_fields():
    with pytest.raises(ValueError):
        read_deployment_packet({"id": "DR-X"})


def test_read_packet_round_trips():
    packet = read_deployment_packet(_packet())
    assert packet.id == "DR-T01"
    assert packet.customer == "Test Customer"


@pytest.mark.parametrize(
    "system_kwargs,expected",
    [
        ({"data_quality": "clean", "custom_code": "none"}, "clean"),
        ({"data_quality": "conflict"}, "conflict"),
        ({"data_quality": "partial"}, "partial"),
        ({"data_quality": "missing", "records": None}, "missing"),
        ({"custom_code": "remediation-required"}, "remediation"),
    ],
)
def test_fit_gap_statuses(system_kwargs, expected):
    packet = packet_from_dict(_packet(legacy_systems=[_system(**system_kwargs)]))
    items = analyze_fit_gap(packet)
    assert len(items) == 1
    assert items[0].status == expected
    assert items[0].source == "SAP ECC 6.0:Finance"


@pytest.mark.parametrize(
    "decision,prefix",
    [
        ("GO", "GO"),
        ("HOLD", "NO-GO"),
        ("PAUSE", "NO-GO"),
        ("BLOCK", "NO-GO"),
    ],
)
def test_checklist_verdicts(decision, prefix):
    packet = packet_from_dict(_packet(legacy_systems=[_system()]))
    items = analyze_fit_gap(packet)
    entries, verdict = compile_cutover_checklist(packet, items, decision)
    assert verdict.startswith(prefix)
    assert entries[0].status == "ready"
    assert entries[0].source == "SAP ECC 6.0:Finance"


def test_checklist_blocks_conflicted_items():
    packet = packet_from_dict(_packet(legacy_systems=[_system(data_quality="conflict")]))
    items = analyze_fit_gap(packet)
    entries, _ = compile_cutover_checklist(packet, items, "PAUSE")
    assert entries[0].status == "blocked"
