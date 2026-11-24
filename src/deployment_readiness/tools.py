"""The three allowlisted tools. Nothing else may touch a packet.

1. read_packet — load and validate a deployment packet.
2. analyze_fit_gap — per-system fit-gap status from the inventory.
3. compile_cutover_checklist — go/no-go checklist from the fit-gap + decision.
"""

from __future__ import annotations

from dataclasses import dataclass

from deployment_readiness.packet import Packet, packet_from_dict

ALLOWED_TOOLS = (
    "read_deployment_packet",
    "analyze_fit_gap",
    "compile_cutover_checklist",
)


@dataclass(frozen=True)
class FitGapItem:
    """One legacy system's fit-gap verdict."""

    system: str
    module: str
    status: str  # clean | conflict | partial | missing | remediation
    detail: str
    source: str


@dataclass(frozen=True)
class ChecklistEntry:
    """One cutover-readiness checklist line, always sourced."""

    item: str
    status: str  # ready | blocked | verify
    source: str


def read_deployment_packet(data: dict) -> Packet:
    """Tool 1: load and validate a packet. Raises ValueError if malformed."""
    return packet_from_dict(data)


def analyze_fit_gap(packet: Packet) -> list[FitGapItem]:
    """Tool 2: per-system fit-gap status, derived only from the inventory."""
    items = []
    for system in packet.legacy_systems:
        source = f"{system.name}:{system.module}"
        if system.data_quality == "conflict":
            items.append(
                FitGapItem(
                    system=system.name,
                    module=system.module,
                    status="conflict",
                    detail="Conflicting records across systems for this module.",
                    source=source,
                )
            )
        elif system.data_quality == "partial":
            items.append(
                FitGapItem(
                    system=system.name,
                    module=system.module,
                    status="partial",
                    detail="Partial match: some records reconcile, some do not.",
                    source=source,
                )
            )
        elif system.data_quality == "missing" or system.records is None:
            items.append(
                FitGapItem(
                    system=system.name,
                    module=system.module,
                    status="missing",
                    detail="Required evidence absent: record count or inventory unknown.",
                    source=source,
                )
            )
        elif system.custom_code == "remediation-required":
            items.append(
                FitGapItem(
                    system=system.name,
                    module=system.module,
                    status="remediation",
                    detail="Legacy custom code must be remediated before cutover.",
                    source=source,
                )
            )
        else:
            items.append(
                FitGapItem(
                    system=system.name,
                    module=system.module,
                    status="clean",
                    detail="Maps cleanly to the target system; no remediation needed.",
                    source=source,
                )
            )
    return items


def compile_cutover_checklist(
    packet: Packet, fit_gap: list[FitGapItem], decision: str
) -> tuple[list[ChecklistEntry], str]:
    """Tool 3: cutover-readiness checklist + go/no-go verdict.

    Every entry cites the packet source it rests on. The verdict is never
    GO unless the decision is GO; a HOLD/PAUSE/BLOCK decision is a NO-GO.
    """
    entries = []
    for item in fit_gap:
        if item.status == "clean":
            entries.append(
                ChecklistEntry(
                    item=f"Verify {item.system} {item.module} reconciles to target",
                    status="ready",
                    source=item.source,
                )
            )
        elif item.status == "conflict":
            entries.append(
                ChecklistEntry(
                    item=f"Resolve conflicting records in {item.system} {item.module}",
                    status="blocked",
                    source=item.source,
                )
            )
        elif item.status == "partial":
            entries.append(
                ChecklistEntry(
                    item=f"Reconcile partial match in {item.system} {item.module}",
                    status="blocked",
                    source=item.source,
                )
            )
        elif item.status == "missing":
            entries.append(
                ChecklistEntry(
                    item=f"Gather missing evidence for {item.system} {item.module}",
                    status="blocked",
                    source=item.source,
                )
            )
        else:  # remediation
            entries.append(
                ChecklistEntry(
                    item=f"Remediate legacy custom code in {item.system} {item.module}",
                    status="blocked",
                    source=item.source,
                )
            )
    if decision == "GO":
        verdict = "GO — cutover may proceed after decision-gate approval"
    elif decision == "BLOCK":
        verdict = "NO-GO — injected instruction blocked; packet quarantined"
    elif decision == "PAUSE":
        verdict = "NO-GO — conflicts unresolved; pause for human review"
    else:  # HOLD
        verdict = "NO-GO — evidence or remediation outstanding"
    return entries, verdict
