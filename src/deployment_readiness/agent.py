"""The agent: two human gates around three allowlisted tools.

Gate 1 (plan approval) runs before any tool executes. Gate 2 (decision
approval) runs before any decision is recorded or published — G1: a GO is
only a proposal until a human approves it. An injected instruction (G4)
blocks publication even when both gates are approved.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from deployment_readiness import guardrail
from deployment_readiness.reasoner import LiveReasoner, StubReasoner
from deployment_readiness.tools import (
    ALLOWED_TOOLS,
    ChecklistEntry,
    FitGapItem,
    analyze_fit_gap,
    compile_cutover_checklist,
    read_deployment_packet,
)


@dataclass(frozen=True)
class AgentResult:
    """Everything one agent run produces (or refuses to produce)."""

    packet_id: str
    decision: str  # GO | HOLD | PAUSE | BLOCK | REFUSED
    fit_gap: list[FitGapItem] = field(default_factory=list)
    checklist: list[ChecklistEntry] = field(default_factory=list)
    verdict: str = ""
    flags: dict = field(default_factory=dict)
    published: bool = False
    provenance: list[str] = field(default_factory=list)
    spend_usd: float = 0.0
    gates_checked: list[str] = field(default_factory=list)
    refusal: str = ""


class DeploymentAgent:
    """Bounded deployment-readiness agent."""

    def __init__(self, mode: str = "stub", live_model: str | None = None) -> None:
        if mode not in ("stub", "live"):
            raise ValueError(f"unknown mode: {mode!r}")
        self.mode = mode
        self._live = LiveReasoner(model=live_model) if mode == "live" else None

    def plan(self) -> list[str]:
        """The tool plan, fixed and allowlisted. Gate 1 approves this plan."""
        return list(ALLOWED_TOOLS)

    def run(
        self,
        packet_data: dict,
        *,
        approve_plan: bool,
        approve_decision: bool,
    ) -> AgentResult:
        packet = read_deployment_packet(packet_data)
        if not approve_plan:
            return AgentResult(
                packet_id=packet.id,
                decision="REFUSED",
                refusal="plan gate not approved: no tool ran",
                gates_checked=["plan"],
            )
        fit_gap = analyze_fit_gap(packet)
        injected = guardrail.scan_injection(packet.discovery_notes)
        fabricated = guardrail.scan_fabrication(packet.claims)
        statuses = {(item.system, item.module): item.status for item in fit_gap}
        missing = guardrail.missing_evidence(packet, statuses)
        flags = {
            "injection": [note.text for note in injected],
            "fabrication": [claim.text for claim in fabricated],
            "missing_evidence": missing,
        }
        if self.mode == "live":
            assert self._live is not None
            decision, cost = self._live.decide(packet, fit_gap)
            spend = cost
        else:
            decision = StubReasoner().decide(
                packet, fit_gap, injection=bool(injected), fabrication=bool(fabricated)
            )
            spend = 0.0
        checklist, verdict = compile_cutover_checklist(packet, fit_gap, decision)
        # Gate 2 (G1): nothing is published without decision approval, and an
        # injected instruction blocks publication even when approved.
        published = bool(approve_decision) and decision != "BLOCK"
        return AgentResult(
            packet_id=packet.id,
            decision=decision,
            fit_gap=fit_gap,
            checklist=checklist,
            verdict=verdict,
            flags=flags,
            published=published,
            provenance=guardrail.cited_sources(packet),
            spend_usd=spend,
            gates_checked=["plan", "decision"],
        )
