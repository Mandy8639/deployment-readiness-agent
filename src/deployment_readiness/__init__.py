"""Deployment-readiness agent: bounded, governed, human-gated.

Takes a customer deployment packet (discovery notes, legacy-system inventory,
claims) and produces a fit-gap analysis, a deployment decision, and a
cutover-readiness checklist. A deterministic guardrail (G1-G5) and two human
gates bound every run. The default reasoner is a deterministic stub ($0.00);
an optional live Anthropic mode is capped at $1.00/day.
"""

__version__ = "0.1.0"

from deployment_readiness.agent import DeploymentAgent
from deployment_readiness.packet import Claim, LegacySystem, Note, Packet

__all__ = ["Claim", "DeploymentAgent", "LegacySystem", "Note", "Packet", "__version__"]
