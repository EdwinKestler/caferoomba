"""Runtime policies. ConstantPolicy is PR1; ONNX is used when a file exists."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from caferoomba.schemas import ActionLabel


class ConstantPolicy:
    """Deterministic STOP. Used when no ONNX artifact is configured."""

    def predict(self, frames: np.ndarray) -> dict:
        if frames.ndim != 5:
            raise ValueError("frames must be B,T,C,H,W")
        return {
            "action": ActionLabel.STOP.value,
            "action_label": ActionLabel.STOP,
            "turn180_score": 0.0,
            "requires_cosmos": False,
            "requires_cloud": False,
            "backend": "constant-stop",
        }


def load_policy(onnx_path: str | None):
    if not onnx_path:
        return ConstantPolicy()
    path = Path(onnx_path)
    if not path.is_file():
        raise FileNotFoundError(f"configured policy artifact is missing: {path}")
    from caferoomba.deployment.inference import OnboardPolicy

    return OnboardPolicy(path)
