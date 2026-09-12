from pathlib import Path

import numpy as np
import pytest
import torch

from caferoomba.data.fixtures import build_synthetic_clips
from caferoomba.deployment.export_onnx import export_onnx
from caferoomba.learning.dataset import load_clip_stack
from caferoomba.learning.train import train_steps


def test_export_representative_parity_and_rejects_empty(tmp_path):
    torch.set_num_threads(2)
    clips = build_synthetic_clips(tmp_path / "frames")
    checkpoint = Path(train_steps(clips, output_dir=tmp_path / "train")["checkpoint"])
    out = tmp_path / "student.onnx"
    samples = [load_clip_stack(c, size=64)[None, ...] for c in clips[:2]]
    report = export_onnx(checkpoint, out, validation_frames=iter(samples))
    assert report["validation_samples"] == 2
    assert report["validation_kind"] == "representative"
    assert report["agrees"] and len(report["onnx_sha256"]) == 64
    original = out.read_bytes()
    with pytest.raises(ValueError, match="agreement"):
        export_onnx(checkpoint, out, validation_frames=[])
    assert out.read_bytes() == original
    samples[0][:] = np.nan
    with pytest.raises(ValueError, match="invalid representative"):
        export_onnx(checkpoint, out, validation_frames=samples)
    assert out.read_bytes() == original


def test_real_checkpoint_requires_representative_input(tmp_path):
    clips = build_synthetic_clips(tmp_path / "frames")
    checkpoint = Path(train_steps(clips, output_dir=tmp_path / "train")["checkpoint"])
    blob = torch.load(checkpoint, weights_only=False)
    blob["is_synthetic"] = False
    torch.save(blob, checkpoint)
    with pytest.raises(ValueError, match="representative"):
        export_onnx(checkpoint, tmp_path / "student.onnx")
    assert not (tmp_path / "student.onnx").exists()
