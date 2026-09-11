"""Onboard student inference. Requires no teacher, GPU, or credentials."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from caferoomba.schemas import CLASS_ORDER, ActionLabel


class OnboardPolicy:
    def __init__(self, onnx_path: Path) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    def predict(self, frames: np.ndarray) -> dict:
        if frames.ndim != 5:
            raise ValueError("frames must be B,T,C,H,W")
        if not np.isfinite(frames).all():
            raise ValueError("non-finite frames")
        action_logits, turn_logit = self.session.run(None, {"frames": frames.astype(np.float32)})
        index = int(np.argmax(action_logits[0]))
        return {
            "action": CLASS_ORDER[index],
            "action_label": ActionLabel(CLASS_ORDER[index]),
            "turn180_score": float(1 / (1 + np.exp(-turn_logit[0]))),
            "requires_cosmos": False,
            "requires_cloud": False,
        }
