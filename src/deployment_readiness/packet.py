"""Deployment packet: the single input to the agent.

A packet is a synthetic customer engagement record: discovery notes from
workshops, a legacy-system inventory, and claims made about the engagement.
Every note and claim carries a provenance source; a claim without a source is
unsourced by construction and the guardrail treats it as fabrication.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Note:
    """One discovery note. ``source`` names where it came from."""

    text: str
    source: str


@dataclass(frozen=True)
class LegacySystem:
    """One legacy system in scope for the migration.

    ``data_quality`` is one of clean / conflict / partial / missing.
    ``custom_code`` is one of none / remediation-required.
    ``records`` is None when the record count is unknown (missing evidence).
    """

    name: str
    module: str
    records: int | None
    data_quality: str
    custom_code: str


@dataclass(frozen=True)
class Claim:
    """One claim about the engagement. ``source`` may be None (unsourced)."""

    text: str
    source: str | None


@dataclass(frozen=True)
class Packet:
    """A deployment packet. All fields are required; see tools.read_packet."""

    id: str
    category: str
    customer: str
    target_system: str
    discovery_notes: list[Note] = field(default_factory=list)
    legacy_systems: list[LegacySystem] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)


def packet_from_dict(data: dict) -> Packet:
    """Build a Packet from a plain dict, validating required fields."""
    required = ["id", "category", "customer", "target_system"]
    for key in required:
        if key not in data or data[key] in (None, ""):
            raise ValueError(f"packet is missing required field: {key}")
    notes = [Note(text=n["text"], source=n["source"]) for n in data.get("discovery_notes", [])]
    systems = [
        LegacySystem(
            name=s["name"],
            module=s["module"],
            records=s.get("records"),
            data_quality=s["data_quality"],
            custom_code=s["custom_code"],
        )
        for s in data.get("legacy_systems", [])
    ]
    claims = [Claim(text=c["text"], source=c.get("source")) for c in data.get("claims", [])]
    return Packet(
        id=data["id"],
        category=data["category"],
        customer=data["customer"],
        target_system=data["target_system"],
        discovery_notes=notes,
        legacy_systems=systems,
        claims=claims,
        required_evidence=list(data.get("required_evidence", [])),
    )


def packet_to_dict(packet: Packet) -> dict:
    """Serialise a Packet back to a plain dict."""
    return {
        "id": packet.id,
        "category": packet.category,
        "customer": packet.customer,
        "target_system": packet.target_system,
        "discovery_notes": [{"text": n.text, "source": n.source} for n in packet.discovery_notes],
        "legacy_systems": [
            {
                "name": s.name,
                "module": s.module,
                "records": s.records,
                "data_quality": s.data_quality,
                "custom_code": s.custom_code,
            }
            for s in packet.legacy_systems
        ],
        "claims": [{"text": c.text, "source": c.source} for c in packet.claims],
        "required_evidence": list(packet.required_evidence),
    }
