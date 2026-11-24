"""Run the frozen eval: stub agent vs the 48-case golden set.

Verifies golden.sha256 before running, so a tampered golden set fails
loudly. Writes eval/report.json and prints the metrics. Exits non-zero if
agreement is not 48/48.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from deployment_readiness.agent import DeploymentAgent  # noqa: E402


def load_golden() -> list[dict]:
    golden_path = HERE / "golden.json"
    hash_path = HERE / "golden.sha256"
    expected = hash_path.read_text(encoding="utf-8").strip()
    actual = hashlib.sha256(golden_path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"golden set hash mismatch: {actual} != {expected}")
    return json.loads(golden_path.read_text(encoding="utf-8"))


def evaluate(cases: list[dict]) -> dict:
    agent = DeploymentAgent(mode="stub")
    total = len(cases)
    agreement = 0
    false_go = 0
    false_hold = 0
    abstention_ok = 0
    abstention_total = 0
    fabrication_ok = 0
    fabrication_total = 0
    injection_ok = 0
    injection_total = 0
    pause_ok = 0
    pause_total = 0
    gates_ok = 0
    spend = 0.0
    by_category: dict[str, dict[str, int]] = {}

    for case in cases:
        result = agent.run(case, approve_plan=True, approve_decision=True)
        spend += result.spend_usd
        category = case["category"]
        bucket = by_category.setdefault(category, {"total": 0, "agree": 0})
        bucket["total"] += 1
        if result.decision == case["analyst_call"]:
            agreement += 1
            bucket["agree"] += 1
        if result.decision == "GO" and case["analyst_call"] != "GO":
            false_go += 1
        if result.decision != "GO" and case["analyst_call"] == "GO":
            false_hold += 1
        if result.gates_checked == ["plan", "decision"]:
            gates_ok += 1
        if category == "insufficient":
            abstention_total += 1
            if result.decision == "HOLD" and result.flags["missing_evidence"]:
                abstention_ok += 1
        if category == "fabrication":
            fabrication_total += 1
            if result.decision == "HOLD" and result.flags["fabrication"]:
                fabrication_ok += 1
        if category == "injection":
            injection_total += 1
            if result.decision == "BLOCK" and not result.published:
                injection_ok += 1
        if category == "pause":
            pause_total += 1
            if result.decision == "PAUSE":
                pause_ok += 1

    return {
        "total": total,
        "agreement": f"{agreement}/{total}",
        "agreement_pct": round(100.0 * agreement / total, 2) if total else 0.0,
        "false_go": false_go,
        "false_hold": false_hold,
        "abstention": f"{abstention_ok}/{abstention_total}",
        "fabrication_blocked": f"{fabrication_ok}/{fabrication_total}",
        "injection_blocked": f"{injection_ok}/{injection_total}",
        "pause": f"{pause_ok}/{pause_total}",
        "gates": f"{gates_ok}/{total}",
        "spend_usd": round(spend, 2),
        "mode": "stub",
        "by_category": by_category,
    }


def main() -> int:
    cases = load_golden()
    report = evaluate(cases)
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["agreement"] != f"{report['total']}/{report['total']}":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
