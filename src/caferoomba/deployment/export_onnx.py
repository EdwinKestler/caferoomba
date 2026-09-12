"""Static-shape ONNX export and numerical agreement vs PyTorch."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import torch

from caferoomba.data.ingest import sha256_file
from caferoomba.learning.train import load_checkpoint
from caferoomba.schemas import CLASS_ORDER


class ExportWrapper(torch.nn.Module):
    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, frames: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        out = self.model(frames)
        return out["action_logits"], out["turn_logit"]


def export_onnx(checkpoint: Path, onnx_path: Path, *, opset: int = 17,
                validation_frames: Iterable[np.ndarray] | None = None) -> dict:
    blob = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = load_checkpoint(checkpoint)
    wrapper = ExportWrapper(model).eval()
    dummy = torch.zeros(1, blob["in_frames"], 3, blob["image_size"], blob["image_size"])
    if validation_frames is None and not blob.get("is_synthetic", True):
        raise ValueError("real-data export requires representative validation frames")
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    import onnxruntime as ort
    fd, name = tempfile.mkstemp(suffix=".onnx", dir=onnx_path.parent)
    os.close(fd)
    temporary = Path(name)
    action_err = turn_err = 0.0
    checked = 0
    try:
        torch.onnx.export(wrapper, dummy, temporary, input_names=["frames"],
                          output_names=["action_logits", "turn_logit"],
                          opset_version=opset, dynamo=False)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        session = ort.InferenceSession(str(temporary), sess_options=options,
                                       providers=["CPUExecutionProvider"])
        samples = [dummy.numpy()] if validation_frames is None else validation_frames
        for sample in samples:
            sample = np.asarray(sample, dtype=np.float32)
            if (tuple(sample.shape) != tuple(dummy.shape) or not np.isfinite(sample).all()
                    or sample.min() < 0 or sample.max() > 1):
                raise ValueError("invalid representative RGB input")
            with torch.no_grad():
                pt_action, pt_turn = wrapper(torch.from_numpy(sample))
            ort_action, ort_turn = session.run(None, {"frames": sample})
            if not all(np.isfinite(x).all() for x in
                       (pt_action.numpy(), pt_turn.numpy(), ort_action, ort_turn)):
                raise ValueError("non-finite export output")
            action_err = max(action_err, float(np.max(np.abs(pt_action.numpy() - ort_action))))
            turn_err = max(turn_err, float(np.max(np.abs(pt_turn.numpy() - ort_turn))))
            checked += 1
        if checked == 0 or action_err >= 1e-4 or turn_err >= 1e-4:
            raise ValueError("ONNX representative numerical agreement failed")
        os.replace(temporary, onnx_path)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "onnx": str(onnx_path),
        "onnx_sha256": sha256_file(onnx_path),
        "checkpoint_sha256": sha256_file(checkpoint),
        "dataset_sha256": blob.get("dataset_sha256"),
        "split_fingerprints": blob.get("split_fingerprints", {}),
        "provenance": blob.get("provenance", {}),
        "validation_samples": checked,
        "validation_kind": "zero_fixture" if validation_frames is None else "representative",
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
