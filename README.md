# deployment-readiness-agent

A bounded deployment-readiness agent for enterprise ERP modernization
engagements — the kind of work a Deployment Strategist does at Tessera Labs:
take a messy customer discovery packet, produce a fit-gap analysis, a
deployment decision, and a cutover-readiness checklist, with a deterministic
guardrail and two human gates around every run.

## What it does

Given a deployment packet (discovery notes, legacy-system inventory, claims
about the engagement), the agent:

1. **Reads the packet** — validates it (tool 1 of 3 allowlisted tools).
2. **Analyses the fit-gap** — per-system verdict: clean, conflict, partial,
   missing, or remediation (tool 2).
3. **Decides** — GO, HOLD, PAUSE, or BLOCK.
4. **Compiles a cutover checklist** — go/no-go verdict with sourced entries
   (tool 3).

Nothing else may touch a packet. There are exactly three tools.

## The guardrail (G1–G5)

| Rule | Behaviour |
| --- | --- |
| G1 | A GO is only a proposal until a human approves the decision gate. |
| G2 | Only sourced claims may be cited. An unsourced claim is dropped and the packet holds. |
| G3 | Missing evidence means abstain: the agent holds instead of guessing. |
| G4 | Instructions injected into discovery notes are blocked; nothing is published. |
| G5 | Conflicting or partial records pause the run for human review. |

Two human gates bound every run: **plan approval** (before any tool runs)
and **decision approval** (before anything is recorded or published).

## Verified numbers (frozen stub eval, 48 cases)

| Metric | Result |
| --- | --- |
| Agreement with analyst calls | 48/48 (100%) |
| False go-lives | 0 |
| False holds | 0 |
| Abstention (insufficient evidence) | 6/6 |
| Fabrication blocked | 6/6 |
| Injection blocked | 6/6 |
| Pause (partial match) | 4/4 |
| Gates checked | 48/48 |
| Spend | $0.00 (stub mode) |
| Tests | 51 passed |

The golden set is frozen and hash-locked (`eval/golden.sha256`); the eval
refuses to run on a tampered set. Reproduce it with:

```bash
python eval/run_eval.py
```

## Honest limits

- The eval is **synthetic**: it measures the deterministic stub against 48
  frozen cases built for this repo, not real-world deployment performance.
  Each case carries exactly one signal, so the numbers show the guardrail
  and decision rule behave as designed — not that the agent understands
  real ERP migrations.
- The stub reasoner is rule-based. It cannot read a real customer's
  systems, and it should never be the only reviewer of a cutover.
- Live mode exists but is deliberately narrow (see below).

## Usage

```python
from deployment_readiness.agent import DeploymentAgent

agent = DeploymentAgent(mode="stub")
result = agent.run(packet_dict, approve_plan=True, approve_decision=True)
print(result.decision)  # GO | HOLD | PAUSE | BLOCK | REFUSED
print(result.verdict)  # go/no-go verdict
print(result.checklist)  # sourced cutover-readiness entries
```

## MCP server

The three tools are exposed over MCP (stdio, no external dependencies):

```bash
python -m deployment_readiness.mcp_server
```

## Live mode (optional)

Set `DEPLOYMENT_MODE=live` with `ANTHROPIC_API_KEY` and install the live
extra (`pip install '.[live]'`). Live mode is capped at **$1.00/day** and
only accepts models in the priced-model table (`claude-haiku-4-5`,
$1.00/$5.00 per MTok input/output, per Anthropic's published pricing).
Unknown models are refused; without an API key it refuses outright. The
eval never uses live mode.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e . ruff pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python -m pytest -q
```

## Why this exists

Built for a Tessera Labs Deployment Strategist application. Tessera's
platform (Mosaic) sells governed, traceable, reversible ERP modernization
with human approval gates — this agent is a small, honest version of that
same shape: discovery in, fit-gap out, nothing irreversible without a human.
