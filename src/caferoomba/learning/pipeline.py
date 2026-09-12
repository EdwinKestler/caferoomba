"""Persistent notebook handoffs; human-label training, no remote API calls."""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import torch

from caferoomba.data.ingest import sha256_file
from caferoomba.data.prepare import load_prepared_dataset
from caferoomba.deployment.export_onnx import export_onnx
from caferoomba.learning.dataset import load_clip_stack
from caferoomba.learning.evaluate import evaluate_clips
from caferoomba.learning.train import load_checkpoint, train_epochs


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".report-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def _run_lock(run_dir: Path):
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    with (run_dir.parent / f".{run_dir.name}.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another process owns this training run") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _dataset(manifest: Path):
    clips = load_prepared_dataset(manifest)
    metadata = json.loads(manifest.read_text())
    return clips, metadata


def train_run(manifest: Path, run_dir: Path, *, epochs: int = 10, batch_size: int = 8,
              image_size: int = 64, lr: float = 1e-3, seed: int = 0,
              device: str = "cpu", resume: Path | None = None) -> dict:
    """Train every training example, select on validation, never evaluate test."""
    clips, metadata = _dataset(manifest)
    with _run_lock(run_dir):
        if (run_dir / "test_metrics.json").exists():
            raise ValueError("test already evaluated; use a new run for further training")
        if resume is None and run_dir.exists() and any(run_dir.iterdir()):
            raise FileExistsError("run already exists; explicitly resume or choose a new run")
        report = train_epochs(
            clips, output_dir=run_dir, epochs=epochs, batch_size=batch_size, lr=lr,
            image_size=image_size, in_frames=metadata["config"]["frame_count"],
            seed=seed, device=device, resume=resume,
            dataset_sha256=metadata["dataset_sha256"],
        )
        # Store relative checkpoint locations so a complete run can move between runtimes.
        report = dict(report)
        report["checkpoint"] = Path(report["checkpoint"]).name
        report["last_checkpoint"] = Path(report["last_checkpoint"]).name
        if "best_checkpoint" in report:
            report["best_checkpoint"] = Path(report["best_checkpoint"]).name
        report["dataset_sha256"] = metadata["dataset_sha256"]
        report["checkpoint_sha256"] = sha256_file(run_dir / report["checkpoint"])
        report["preprocessing"] = {
            "color": "RGB", "normalization": "uint8 / 255", "image_size": image_size,
            "frame_count": metadata["config"]["frame_count"],
            "period_ms": metadata["config"]["period_ms"],
        }
        _save_json(run_dir / "training_report.json", report)
    return report


def _selected(run_dir: Path, metadata: dict):
    report = json.loads((run_dir / "training_report.json").read_text())
    relative = Path(report["checkpoint"])
    if relative.name != str(relative) or relative.is_absolute():
        raise ValueError("checkpoint must be a filename within the run")
    checkpoint = run_dir / relative
    if not checkpoint.resolve().is_relative_to(run_dir.resolve()):
        raise ValueError("checkpoint escapes run directory")
    if (report["dataset_sha256"] != metadata["dataset_sha256"] or
            report["checkpoint_sha256"] != sha256_file(checkpoint)):
        raise ValueError("dataset/checkpoint differs from training report")
    # Only load trusted local checkpoints, never arbitrary uploaded Torch files.
    blob = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if blob.get("dataset_sha256") != metadata["dataset_sha256"]:
        raise ValueError("checkpoint dataset identity mismatch")
    return checkpoint, blob, report


def evaluate_run(manifest: Path, run_dir: Path) -> dict:
    """Final test evaluation of the validation-selected checkpoint; cache the result."""
    clips, metadata = _dataset(manifest)
    with _run_lock(run_dir):
        checkpoint, blob, report = _selected(run_dir, metadata)
        destination = run_dir / "test_metrics.json"
        if destination.exists():
            saved = json.loads(destination.read_text())
            if (saved["checkpoint_sha256"] != report["checkpoint_sha256"] or
                    saved["dataset_sha256"] != metadata["dataset_sha256"]):
                raise ValueError("existing evaluation belongs to different artifacts")
            return saved
        metrics = evaluate_clips(load_checkpoint(checkpoint), clips,
                                 image_size=blob["image_size"], split="test")
        metrics.update(checkpoint_sha256=report["checkpoint_sha256"],
                       dataset_sha256=metadata["dataset_sha256"])
        _save_json(destination, metrics)
        return json.loads(destination.read_text())


def export_run(manifest: Path, run_dir: Path, *, max_samples: int = 16) -> dict:
    """Export the selected checkpoint and compare outputs on validation frames."""
    if max_samples < 1:
        raise ValueError("max_samples must be positive")
    clips, metadata = _dataset(manifest)
    with _run_lock(run_dir):
        checkpoint, blob, report = _selected(run_dir, metadata)
        validation = [clip for clip in clips if clip.split == "val"][:max_samples]
        if not validation:
            raise ValueError("representative validation clips are required")
        exported = export_onnx(
            checkpoint, run_dir / "student.onnx",
            validation_frames=(load_clip_stack(c, size=blob["image_size"])[None, ...]
                               for c in validation),
        )
        exported.update(onnx="student.onnx", preprocessing=report["preprocessing"],
                        validation_clip_ids=[c.clip_id for c in validation])
        _save_json(run_dir / "export_report.json", exported)
        return exported
