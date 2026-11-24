"""Eval tests: the frozen golden set reproduces its committed report."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_run_eval():
    spec = importlib.util.spec_from_file_location("run_eval", ROOT / "eval" / "run_eval.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_golden_set_is_frozen_and_complete():
    run_eval = _load_run_eval()
    cases = run_eval.load_golden()  # raises on a hash mismatch
    assert len(cases) == 48
    categories = {}
    for case in cases:
        categories[case["category"]] = categories.get(case["category"], 0) + 1
    assert categories == {
        "clean": 12,
        "data-conflict": 8,
        "remediation": 6,
        "insufficient": 6,
        "fabrication": 6,
        "injection": 6,
        "pause": 4,
    }


def test_stub_eval_reproduces_committed_report():
    run_eval = _load_run_eval()
    cases = run_eval.load_golden()
    report = run_eval.evaluate(cases)
    assert report["agreement"] == "48/48"
    assert report["agreement_pct"] == 100.0
    assert report["false_go"] == 0
    assert report["false_hold"] == 0
    assert report["abstention"] == "6/6"
    assert report["fabrication_blocked"] == "6/6"
    assert report["injection_blocked"] == "6/6"
    assert report["pause"] == "4/4"
    assert report["gates"] == "48/48"
    assert report["spend_usd"] == 0.0
    assert report["mode"] == "stub"
