"""Static repository policy checks; these do not prove account/model availability."""

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_root_routing_preserves_permission_inheritance():
    config = tomllib.loads((ROOT / ".codex/config.toml").read_text())
    assert config == {
        "model": "gpt-6-astra",
        "model_reasoning_effort": "medium",
        "agents": {
            "enabled": True,
            "default_subagent_model": "gpt-5.6-luna",
            "default_subagent_reasoning_effort": "max",
        },
    }


@pytest.mark.parametrize("role,model,effort", [
    ("explorer", "gpt-5.6-luna", "max"),
    ("worker", "gpt-5.6-sol", "high"),
    ("researcher", "gpt-5.6-luna", "max"),
    ("reviewer", "gpt-6-astra", "xhigh"),
])
def test_named_role_contract(role, model, effort):
    config = tomllib.loads((ROOT / f".codex/agents/{role}.toml").read_text())
    assert set(config) == {
        "name", "description", "developer_instructions", "model", "model_reasoning_effort",
    }
    assert config["name"] == role
    assert config["model"] == model
    assert config["model_reasoning_effort"] == effort
    assert config["description"].strip()
    assert "Project Memory" in config["developer_instructions"]
    assert "Do not spawn further agents" in config["developer_instructions"]
