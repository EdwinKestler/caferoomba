"""Execution provider selection must never silently change the runtime target."""
import sys
from types import SimpleNamespace

import pytest

from caferoomba.deployment.inference import OnboardPolicy


def test_unavailable_accelerator_fails_before_model_load(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "onnxruntime", SimpleNamespace(
        get_available_providers=lambda: ["CPUExecutionProvider"]
    ))
    with pytest.raises(RuntimeError, match="unavailable"):
        OnboardPolicy(tmp_path / "absent.onnx", execution_providers=("CUDAExecutionProvider",))


@pytest.mark.parametrize("fallback", [True, False])
def test_provider_initialization_fallback_rejected(monkeypatch, tmp_path, fallback):
    model = tmp_path / "student.onnx"
    model.write_bytes(b"mock model")

    class Options:
        def add_session_config_entry(self, key, value):
            assert (key, value) == ("session.disable_cpu_ep_fallback", "1")

    class Session:
        def __init__(self, *args, **kwargs):
            pass

        def disable_fallback(self):
            pass

        def get_providers(self):
            return ["CPUExecutionProvider"] if fallback else [
                "CUDAExecutionProvider", "CPUExecutionProvider"
            ]

        def get_inputs(self):
            return [SimpleNamespace(name="frames", shape=[1, 8, 3, 64, 64])]

        def get_outputs(self):
            return [SimpleNamespace(name=n) for n in ["action_logits", "turn_logit"]]

    monkeypatch.setitem(sys.modules, "onnxruntime", SimpleNamespace(
        get_available_providers=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"],
        SessionOptions=Options, InferenceSession=Session,
    ))
    if fallback:
        with pytest.raises(RuntimeError, match="fallback"):
            OnboardPolicy(model, execution_providers=("CUDAExecutionProvider",))
    else:
        policy = OnboardPolicy(model, execution_providers=("CUDAExecutionProvider",))
        assert policy.requested_execution_providers == ["CUDAExecutionProvider"]
