"""Live-mode tests: every refusal path, no model call is ever made."""

import json
from datetime import date

import pytest

from deployment_readiness.packet import packet_from_dict
from deployment_readiness.reasoner import DEFAULT_MODEL, PRICED_MODELS, LiveReasoner
from deployment_readiness.tools import analyze_fit_gap


def _packet():
    return packet_from_dict(
        {
            "id": "DR-L01",
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
            "claims": [],
            "required_evidence": [],
        }
    )


def test_priced_model_table_is_not_empty():
    assert DEFAULT_MODEL in PRICED_MODELS
    assert PRICED_MODELS[DEFAULT_MODEL]["input_usd_per_mtok"] > 0


def test_live_refuses_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    reasoner = LiveReasoner(spend_path=str(tmp_path / "spend.json"))
    with pytest.raises(RuntimeError, match="no ANTHROPIC_API_KEY"):
        reasoner.decide(_packet(), analyze_fit_gap(_packet()))


def test_live_refuses_unknown_model(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    reasoner = LiveReasoner(model="claude-opus-99", spend_path=str(tmp_path / "spend.json"))
    with pytest.raises(RuntimeError, match="not in the priced-model table"):
        reasoner.decide(_packet(), analyze_fit_gap(_packet()))


def test_live_refuses_when_daily_cap_reached(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    spend_path = tmp_path / "spend.json"
    spend_path.write_text(json.dumps({"date": date.today().isoformat(), "spent_usd": 1.00}))
    reasoner = LiveReasoner(spend_path=str(spend_path))
    with pytest.raises(RuntimeError, match="daily cap"):
        reasoner.decide(_packet(), analyze_fit_gap(_packet()))
