"""Exercise persistent notebook stage boundaries without cloud or owner data."""
import json
from pathlib import Path

import pytest
import torch

from caferoomba.data.fixtures import build_synthetic_clips


def _notebook_stage(name, scope):
    notebook = json.loads((Path("notebooks") / name).read_text())
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        if set(cell["metadata"].get("tags", [])) & {"bootstrap", "configuration"}:
            continue
        exec(compile("".join(cell["source"]), name, "exec"), scope)


def test_training_notebook_handoff_and_resume_guard(tmp_path, monkeypatch):
    import os

    from caferoomba.learning import pipeline

    torch.set_num_threads(2)
    clips = build_synthetic_clips(tmp_path / "frames")
    metadata = {"dataset_sha256": "a" * 64, "config": {"frame_count": 8, "period_ms": 250}}
    monkeypatch.setattr(pipeline, "_dataset", lambda _path: (clips, metadata))
    monkeypatch.setattr("caferoomba.data.prepare.load_prepared_dataset", lambda _path: clips)
    monkeypatch.setenv("CAFEROOMBA_EPOCHS", "1")
    monkeypatch.setenv("CAFEROOMBA_TRAIN_DEVICE", "cpu")
    monkeypatch.setenv("CAFEROOMBA_BATCH_SIZE", "2")
    monkeypatch.delenv("CAFEROOMBA_RESUME", raising=False)
    manifest, run = tmp_path / "manifest.json", tmp_path / "run"
    interrupted = tmp_path / "interrupted"
    interrupted.mkdir()
    (interrupted / "last.pt").write_bytes(b"existing checkpoint")
    with pytest.raises(FileExistsError):
        pipeline.train_run(manifest, interrupted, epochs=1)
    scope = {"os": os, "Path": Path, "MANIFEST": manifest, "RUN": run}
    _notebook_stage("02_train_and_evaluate.ipynb", scope)
    assert not (run / "test_metrics.json").exists()
    checkpoint_hash = scope["report"]["checkpoint_sha256"]
    with pytest.raises(FileExistsError):
        pipeline.train_run(manifest, run, epochs=1, batch_size=2)
    # Explicit resume before final evaluation.
    pipeline.train_run(manifest, run, epochs=2, batch_size=2, resume=run / "last.pt")
    report = json.loads((run / "training_report.json").read_text())
    assert Path(report["checkpoint"]).name == report["checkpoint"]
    _notebook_stage("03_export_and_replay.ipynb", scope)
    assert scope["metrics"]["n"] == len([c for c in clips if c.split == "test"])
    assert scope["exported"]["checkpoint_sha256"] == report["checkpoint_sha256"]
    assert checkpoint_hash  # prior selection need not be the same after another epoch
    before = (run / "test_metrics.json").read_bytes()
    assert pipeline.evaluate_run(manifest, run) == scope["metrics"]
    assert (run / "test_metrics.json").read_bytes() == before
    with pytest.raises(ValueError, match="test already evaluated"):
        pipeline.train_run(manifest, run, epochs=3, resume=run / "last.pt")
    with (run / report["checkpoint"]).open("ab") as handle:
        handle.write(b"corruption")
    with pytest.raises(ValueError, match="differs"):
        pipeline.export_run(manifest, run)
