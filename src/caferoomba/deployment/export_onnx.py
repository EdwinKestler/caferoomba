"""Static-shape ONNX export and numerical agreement vs PyTorch."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from caferoomba.learning.train import load_checkpoint
from caferoomba.schemas import CLASS_ORDER


class ExportWrapper(torch.nn.Module):
    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, frames: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        out = self.model(frames)
        return out["action_logits"], out["turn_logit"]


def export_onnx(checkpoint: Path, onnx_path: Path, *, opset: int = 17) -> dict:
    blob = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = load_checkpoint(checkpoint)
    wrapper = ExportWrapper(model).eval()
    dummy = torch.zeros(1, blob["in_frames"], 3, blob["image_size"], blob["image_size"])
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapper,
        dummy,
        onnx_path,
        input_names=["frames"],
        output_names=["action_logits", "turn_logit"],
        opset_version=opset,
        dynamo=False,
    )
    with torch.no_grad():
        pt_action, pt_turn = wrapper(dummy)
    import onnxruntime as ort

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_action, ort_turn = session.run(None, {"frames": dummy.numpy()})
    action_err = float(np.max(np.abs(pt_action.numpy() - ort_action)))
    turn_err = float(np.max(np.abs(pt_turn.numpy() - ort_turn)))
    return {
        "onnx": str(onnx_path),
        "class_order": list(CLASS_ORDER),
        "input_shape": list(dummy.shape),
        "image_size": blob["image_size"],
        "in_frames": blob["in_frames"],
        "backbone": blob["backbone"],
        "max_abs_error_action": action_err,
        "max_abs_error_turn": turn_err,
        "tolerance": 1e-4,
        "agrees": action_err < 1e-4 and turn_err < 1e-4,
        "device": "cpu",
        "is_synthetic": blob.get("is_synthetic", True),
        "evidence_state": "tested_offline",
    }
