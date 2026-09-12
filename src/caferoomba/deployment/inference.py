"""Canonical ONNX policy; no cloud/teacher/training imports or auto downloads."""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import numpy as np
from caferoomba.schemas import CLASS_ORDER, ActionLabel


class OnboardPolicy:
    def __init__(self, onnx_path: Path):
        import onnxruntime as ort
        self.model_sha256 = hashlib.sha256(onnx_path.read_bytes()).hexdigest()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(onnx_path), sess_options=options,
                                           providers=["CPUExecutionProvider"])
        inputs = self.session.get_inputs()
        if len(inputs) != 1 or inputs[0].name != "frames":
            raise ValueError("policy must expose exactly one frames input")
        self.expected_shape = inputs[0].shape
        if len(self.expected_shape) != 5:
            raise ValueError("policy input must be B,T,C,H,W")
        outputs = [output.name for output in self.session.get_outputs()]
        if outputs != ["action_logits", "turn_logit"]:
            raise ValueError("unrecognized policy output contract")

    def predict(self, frames: np.ndarray) -> dict:
        if frames.ndim != 5 or any(isinstance(expected, int) and expected != actual
                                  for expected, actual in zip(self.expected_shape, frames.shape)):
            raise ValueError(f"frames must match {self.expected_shape}")
        if not np.isfinite(frames).all() or frames.min() < 0 or frames.max() > 1:
            raise ValueError("frames must be finite normalized RGB")
        logits, turn = self.session.run(None, {"frames": frames.astype(np.float32)})
        if logits.shape != (1, len(CLASS_ORDER)) or np.asarray(turn).size != 1:
            raise ValueError("invalid policy output shape")
        if not np.isfinite(logits).all() or not np.isfinite(turn).all():
            raise ValueError("non-finite policy output")
        index = int(np.argmax(logits[0]))
        z = float(np.asarray(turn).reshape(-1)[0])
        score = 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
        return {"action": CLASS_ORDER[index], "action_label": ActionLabel(CLASS_ORDER[index]),
                "turn180_score": score, "requires_cosmos": False, "requires_cloud": False,
                "backend": "onnx-cpu", "model_sha256": self.model_sha256}
