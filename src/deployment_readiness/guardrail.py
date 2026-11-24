"""Deterministic guardrail G1-G5.

Every rule is a pure function over the packet, so the eval can reproduce it
exactly. No rule ever invents evidence: when evidence is missing the agent
abstains; when instructions appear inside customer notes they are blocked.
"""

from __future__ import annotations

from deployment_readiness.packet import Claim, Note, Packet

# G4: substrings that mark an instruction injected into customer notes.
# A note containing one of these is treated as an attempt to steer the agent,
# not as customer evidence.
INJECTION_PATTERNS = (
    "ignore the",
    "ignore all",
    "override",
    "approve anyway",
    "disregard",
    "do not flag",
    "skip the check",
    "mark this as ready",
    "bypass",
    "pretend",
)


def scan_injection(notes: list[Note]) -> list[Note]:
    """G4: return the notes that carry an injected instruction."""
    hits = []
    for note in notes:
        lowered = note.text.lower()
        if any(pattern in lowered for pattern in INJECTION_PATTERNS):
            hits.append(note)
    return hits


def scan_fabrication(claims: list[Claim]) -> list[Claim]:
    """G2: return the claims with no provenance source. They are dropped."""
    return [claim for claim in claims if not claim.source]


def cited_sources(packet: Packet) -> list[str]:
    """Provenance the agent is allowed to cite: sourced notes and claims only."""
    sources = [note.source for note in packet.discovery_notes]
    sources += [claim.source for claim in packet.claims if claim.source]
    return sorted(set(sources))


def missing_evidence(packet: Packet, fit_gap_statuses: dict[tuple[str, str], str]) -> list[str]:
    """G3: required evidence items with no supporting record.

    Required-evidence entries are ``"Name:Module"`` strings; the identity is
    the (name, module) pair, because two systems can share a name. An item is
    missing when no system matches the entry, or the matching system is
    marked missing.
    """
    missing = []
    by_key = {(system.name, system.module): system for system in packet.legacy_systems}
    for key in packet.required_evidence:
        name, _, module = key.partition(":")
        if (name, module) not in by_key or fit_gap_statuses.get((name, module)) == "missing":
            missing.append(key)
    return missing
