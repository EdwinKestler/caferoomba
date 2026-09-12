"""Deterministic, run-disjoint training with resumable atomic checkpoints."""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import subprocess
import sys
import tempfile
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from caferoomba.data.splits import detect_split_leakage
from caferoomba.learning.dataset import iter_examples
from caferoomba.learning.evaluate import evaluate_clips
from caferoomba.learning.model import build_policy, count_parameters
from caferoomba.schemas import CLASS_ORDER, ClipRecord

CHECKPOINT_FORMAT = "caferoomba.training.v1"
_SPLITS = ("train", "val", "test")


def _batch(examples: list[dict]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    frames = torch.from_numpy(np.stack([item["frames"] for item in examples]))
    action = torch.tensor([item["action"] for item in examples], dtype=torch.long)
    turn = torch.tensor([item["turn180"] for item in examples], dtype=torch.float32)
    return frames, action, turn


def _clip_batch(clips: list[ClipRecord], *, size: int) -> tuple[torch.Tensor, ...]:
    # Images exist only for this batch; the complete dataset is never materialized.
    return _batch(list(iter_examples(clips, size=size)))


def _loss(
    model: nn.Module,
    clips: list[ClipRecord],
    *,
    image_size: int,
    device: torch.device,
) -> torch.Tensor:
    frames, action, turn = _clip_batch(clips, size=image_size)
    frames = frames.to(device)
    action = action.to(device)
    turn = turn.to(device)
    output = model(frames)
    action_loss = F.cross_entropy(output["action_logits"], action)
    turn_loss = F.binary_cross_entropy_with_logits(output["turn_logit"], turn)
    return action_loss + 0.5 * turn_loss


def _split_clips(clips: list[ClipRecord], *, in_frames: int) -> dict[str, list[ClipRecord]]:
    if not clips:
        raise ValueError("training dataset is empty")
    invalid = sorted({str(clip.split) for clip in clips if clip.split not in _SPLITS})
    if invalid:
        raise ValueError(f"every clip must have train/val/test split; invalid: {invalid}")
    leakage = detect_split_leakage(clips)
    if leakage:
        raise ValueError(f"run leakage across splits: {', '.join(sorted(leakage))}")
    grouped = {
        split: sorted(
            (clip for clip in clips if clip.split == split), key=lambda clip: clip.clip_id
        )
        for split in _SPLITS
    }
    empty = [split for split, selected in grouped.items() if not selected]
    if empty:
        raise ValueError(f"non-empty train/val/test splits required; empty: {', '.join(empty)}")
    wrong_frames = [clip.clip_id for clip in clips if clip.window.frame_count != in_frames]
    if wrong_frames:
        raise ValueError(
            f"all clips must contain in_frames={in_frames}; mismatched: {wrong_frames[:3]}"
        )
    duplicate_ids = [
        clip_id
        for clip_id, count in Counter(clip.clip_id for clip in clips).items()
        if count > 1
    ]
    if duplicate_ids:
        raise ValueError(f"duplicate clip ids: {duplicate_ids[:3]}")
    return grouped


def _canonical_clip(clip: ClipRecord) -> bytes:
    payload = clip.model_dump(mode="json")
    # Physical locations are intentionally excluded: a verified manifest and
    # semantic split must remain resumable after moving the dataset directory.
    payload["frame_paths"] = []
    payload["source"]["video_path"] = None
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _update_file_digest(digest: Any, path: str) -> None:
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)


def _fingerprints(
    clips: list[ClipRecord], *, dataset_sha256: str | None
) -> tuple[str, dict[str, str]]:
    split_fingerprints: dict[str, str] = {}
    for split in _SPLITS:
        digest = hashlib.sha256()
        selected = sorted(
            (item for item in clips if item.split == split), key=lambda item: item.clip_id
        )
        for clip in selected:
            digest.update(_canonical_clip(clip))
            digest.update(b"\n")
        split_fingerprints[split] = digest.hexdigest()
    if dataset_sha256 is not None:
        normalized = dataset_sha256.lower()
        if len(normalized) != 64 or any(
            character not in "0123456789abcdef" for character in normalized
        ):
            raise ValueError("dataset_sha256 must be a 64-character hexadecimal digest")
        identity = normalized
    else:
        digest = hashlib.sha256()
        for clip in sorted(clips, key=lambda item: (str(item.split), item.clip_id)):
            digest.update(_canonical_clip(clip))
            for frame_path in clip.frame_paths:
                _update_file_digest(digest, frame_path)
        identity = digest.hexdigest()
    return identity, split_fingerprints


def _provenance() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    revision: str | None = None
    dirty: bool | None = None
    try:
        revision_run = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        revision = revision_run.stdout.strip()
        dirty_run = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        dirty = bool(dirty_run.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        pass
    return {
        "trainer": "caferoomba.learning.train.train_epochs",
        "checkpoint_format": CHECKPOINT_FORMAT,
        "class_order": list(CLASS_ORDER),
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "source_revision": revision,
        "source_dirty": dirty,
    }


def _rng_state(shuffle_generator: torch.Generator) -> dict[str, Any]:
    state: dict[str, Any] = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.get_rng_state(),
        "shuffle": shuffle_generator.get_state(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def _restore_rng(state: dict[str, Any], shuffle_generator: torch.Generator) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"].cpu())
    shuffle_generator.set_state(state["shuffle"].cpu())
    if "torch_cuda" in state and torch.cuda.is_available():
        # map_location may have moved these byte tensors onto the target GPU;
        # CUDA's RNG setter requires CPU byte tensors.
        torch.cuda.set_rng_state_all([item.cpu() for item in state["torch_cuda"]])


def _atomic_torch_save(blob: dict[str, Any], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        torch.save(blob, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def _checkpoint_blob(
    *,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    best_epoch: int,
    best_val_loss: float,
    config: dict[str, Any],
    dataset_sha256: str,
    split_fingerprints: dict[str, str],
    rng_state: dict[str, Any],
    history: list[dict[str, Any]],
    is_synthetic: bool,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "format_version": CHECKPOINT_FORMAT,
        "state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "epoch": epoch,
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "rng_state": rng_state,
        "config": config,
        "dataset_sha256": dataset_sha256,
        "split_fingerprints": split_fingerprints,
        "provenance": provenance,
        "history": history,
        # Top-level compatibility fields are consumed by ONNX export.
        "backbone": config["backbone"],
        "in_frames": config["in_frames"],
        "image_size": config["image_size"],
        "seed": config["seed"],
        "is_synthetic": is_synthetic,
        "parameter_count": count_parameters(model),
    }


def _validate_resume(
    blob: dict[str, Any],
    *,
    config: dict[str, Any],
    dataset_sha256: str,
    split_fingerprints: dict[str, str],
) -> None:
    if blob.get("format_version") != CHECKPOINT_FORMAT:
        raise ValueError("resume checkpoint has unsupported format")
    mismatched = [
        key for key, value in config.items() if blob.get("config", {}).get(key) != value
    ]
    if mismatched:
        raise ValueError(f"resume config mismatch: {', '.join(sorted(mismatched))}")
    if blob.get("dataset_sha256") != dataset_sha256:
        raise ValueError("resume dataset_sha256 mismatch")
    if blob.get("split_fingerprints") != split_fingerprints:
        raise ValueError("resume split fingerprints mismatch")
    required = {"optimizer_state_dict", "rng_state", "epoch", "history"}
    missing = sorted(required.difference(blob))
    if missing:
        raise ValueError(f"resume checkpoint missing: {', '.join(missing)}")
    epoch = blob["epoch"]
    history = blob["history"]
    if not isinstance(epoch, int) or epoch < 1:
        raise ValueError("resume checkpoint has invalid completed epoch")
    if len(history) != epoch or history[-1].get("epoch") != epoch:
        raise ValueError("resume checkpoint epoch/history mismatch")
    required_rng = {"python", "numpy", "torch", "shuffle"}
    missing_rng = sorted(required_rng.difference(blob["rng_state"]))
    if missing_rng:
        raise ValueError(f"resume checkpoint missing RNG state: {', '.join(missing_rng)}")


def _epoch_loss(
    model: nn.Module,
    clips: list[ClipRecord],
    *,
    batch_size: int,
    image_size: int,
    device: torch.device,
) -> tuple[float, int]:
    model.eval()
    total = 0.0
    seen = 0
    batches = 0
    with torch.no_grad():
        for offset in range(0, len(clips), batch_size):
            batch_clips = clips[offset : offset + batch_size]
            batch_loss = _loss(model, batch_clips, image_size=image_size, device=device)
            total += float(batch_loss.item()) * len(batch_clips)
            seen += len(batch_clips)
            batches += 1
    return total / seen, batches


def train_epochs(
    clips: list[ClipRecord],
    *,
    output_dir: Path,
    epochs: int = 1,
    batch_size: int = 8,
    lr: float = 1e-3,
    backbone: str = "tiny",
    image_size: int = 64,
    in_frames: int = 8,
    seed: int = 0,
    device: str = "cpu",
    resume: Path | None = None,
    dataset_sha256: str | None = None,
) -> dict:
    """Train on every train batch and select a checkpoint using validation only."""

    if not isinstance(epochs, int) or epochs < 1:
        raise ValueError("epochs must be >= 1")
    if not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    if not math.isfinite(lr) or lr <= 0:
        raise ValueError("lr must be finite and > 0")
    if image_size < 1:
        raise ValueError("image_size must be >= 1")
    if in_frames < 3:
        raise ValueError("in_frames must be >= 3")
    grouped = _split_clips(clips, in_frames=in_frames)
    identity, split_fingerprints = _fingerprints(clips, dataset_sha256=dataset_sha256)
    config = {
        "batch_size": batch_size,
        "lr": lr,
        "backbone": backbone,
        "image_size": image_size,
        "in_frames": in_frames,
        "seed": seed,
    }
    target_device = torch.device(device)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    shuffle_generator = torch.Generator(device="cpu")
    shuffle_generator.manual_seed(seed)
    model = build_policy(
        backbone=backbone, in_frames=in_frames, image_size=image_size
    ).to(target_device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    start_epoch = 0
    best_epoch = 0
    best_val_loss = float("inf")
    history: list[dict[str, Any]] = []
    best_snapshot: dict[str, Any] | None = None
    output_dir = Path(output_dir)
    best_path = output_dir / "best.pt"
    last_path = output_dir / "last.pt"
    provenance = _provenance()

    if resume is not None:
        blob = torch.load(Path(resume), map_location=target_device, weights_only=False)
        _validate_resume(
            blob,
            config=config,
            dataset_sha256=identity,
            split_fingerprints=split_fingerprints,
        )
        model.load_state_dict(blob["state_dict"])
        optimizer.load_state_dict(blob["optimizer_state_dict"])
        start_epoch = int(blob["epoch"])
        if epochs <= start_epoch:
            raise ValueError(
                f"epochs must exceed completed resume epoch {start_epoch}; got {epochs}"
            )
        best_epoch = int(blob["best_epoch"])
        best_val_loss = float(blob["best_val_loss"])
        history = deepcopy(blob["history"])
        best_snapshot = deepcopy(blob.get("best_snapshot"))
        if best_snapshot is None:
            raise ValueError("resumable checkpoint is missing best_snapshot")
        _restore_rng(blob["rng_state"], shuffle_generator)
        _atomic_torch_save(best_snapshot, best_path)

    is_synthetic = all(clip.source.is_synthetic for clip in clips)
    for epoch_index in range(start_epoch, epochs):
        model.train()
        order = torch.randperm(len(grouped["train"]), generator=shuffle_generator).tolist()
        total_train_loss = 0.0
        train_seen = 0
        train_batches = 0
        for offset in range(0, len(order), batch_size):
            indices = order[offset : offset + batch_size]
            batch_clips = [grouped["train"][index] for index in indices]
            optimizer.zero_grad()
            batch_loss = _loss(model, batch_clips, image_size=image_size, device=target_device)
            if not torch.isfinite(batch_loss).item():
                raise ValueError(f"non-finite training loss at epoch {epoch_index + 1}")
            batch_loss.backward()
            optimizer.step()
            total_train_loss += float(batch_loss.detach().item()) * len(batch_clips)
            train_seen += len(batch_clips)
            train_batches += 1
        train_loss = total_train_loss / train_seen
        val_loss, val_batches = _epoch_loss(
            model,
            grouped["val"],
            batch_size=batch_size,
            image_size=image_size,
            device=target_device,
        )
        if not math.isfinite(val_loss):
            raise ValueError(f"non-finite validation loss at epoch {epoch_index + 1}")
        completed_epoch = epoch_index + 1
        history.append(
            {
                "epoch": completed_epoch,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "train_examples": train_seen,
                "train_batches": train_batches,
                "val_examples": len(grouped["val"]),
                "val_batches": val_batches,
            }
        )
        current_rng = _rng_state(shuffle_generator)
        improved = val_loss < best_val_loss
        if improved:
            best_epoch = completed_epoch
            best_val_loss = val_loss
        current = _checkpoint_blob(
            model=model,
            optimizer=optimizer,
            epoch=completed_epoch,
            best_epoch=best_epoch,
            best_val_loss=best_val_loss,
            config=config,
            dataset_sha256=identity,
            split_fingerprints=split_fingerprints,
            rng_state=current_rng,
            history=history,
            is_synthetic=is_synthetic,
            provenance=provenance,
        )
        if improved:
            best_snapshot = deepcopy(current)
            _atomic_torch_save(best_snapshot, best_path)
        if best_snapshot is None:  # Defensive: the first finite validation loss must improve.
            raise RuntimeError("validation did not produce a selectable checkpoint")
        last = dict(current)
        last["best_snapshot"] = best_snapshot
        _atomic_torch_save(last, last_path)

    best_model = load_checkpoint(best_path, device=device)
    val_metrics = evaluate_clips(
        best_model, clips, image_size=image_size, split="val", device=device
    )
    return {
        "checkpoint": str(best_path),
        "best_checkpoint": str(best_path),
        "last_checkpoint": str(last_path),
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "epochs_completed": epochs,
        "history": history,
        "val_metrics": val_metrics,
        "provenance": provenance,
        "dataset_sha256": identity,
        "split_fingerprints": split_fingerprints,
        "config": config,
        "parameter_count": count_parameters(model),
        "device": str(target_device),
        "backbone": backbone,
        "is_synthetic": is_synthetic,
        "evidence_state": "tested_offline",
    }


def train_steps(
    clips: list[ClipRecord],
    *,
    output_dir: Path,
    steps: int = 1,
    lr: float = 1e-3,
    backbone: str = "tiny",
    image_size: int = 64,
    in_frames: int = 8,
    seed: int = 0,
    device: str = "cpu",
) -> dict:
    """Compatibility smoke trainer; consume successive lazy train batches."""

    if steps < 1:
        raise ValueError("steps must be >= 1")
    if not math.isfinite(lr) or lr <= 0:
        raise ValueError("lr must be finite and > 0")
    training_clips = [clip for clip in clips if clip.split == "train"]
    if not training_clips:
        raise ValueError("no training examples in split 'train'")
    if any(clip.window.frame_count != in_frames for clip in training_clips):
        raise ValueError(f"all training clips must contain in_frames={in_frames}")
    leakage = detect_split_leakage(clips)
    if leakage:
        raise ValueError(f"run leakage across splits: {', '.join(sorted(leakage))}")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    target_device = torch.device(device)
    generator = torch.Generator(device="cpu").manual_seed(seed)
    model = build_policy(
        backbone=backbone, in_frames=in_frames, image_size=image_size
    ).to(target_device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history: list[float] = []
    order: list[int] = []
    offset = 0
    model.train()
    for _step in range(steps):
        if offset >= len(order):
            order = torch.randperm(len(training_clips), generator=generator).tolist()
            offset = 0
        indices = order[offset : offset + 8]
        offset += len(indices)
        batch_clips = [training_clips[index] for index in indices]
        optimizer.zero_grad()
        loss = _loss(model, batch_clips, image_size=image_size, device=target_device)
        if not torch.isfinite(loss).item():
            raise ValueError(f"non-finite training loss at step {_step + 1}")
        loss.backward()
        optimizer.step()
        history.append(float(loss.detach().item()))
    output_dir = Path(output_dir)
    checkpoint = output_dir / "student.pt"
    _atomic_torch_save(
        {
            "format_version": CHECKPOINT_FORMAT,
            "state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "epoch": steps,
            "backbone": backbone,
            "in_frames": in_frames,
            "image_size": image_size,
            "seed": seed,
            "config": {
                "batch_size": 8,
                "lr": lr,
                "backbone": backbone,
                "image_size": image_size,
                "in_frames": in_frames,
                "seed": seed,
            },
            "rng_state": _rng_state(generator),
            "provenance": {
                "trainer": "caferoomba.learning.train.train_steps",
                "checkpoint_format": CHECKPOINT_FORMAT,
                "class_order": list(CLASS_ORDER),
            },
            "is_synthetic": all(clip.source.is_synthetic for clip in training_clips),
            "parameter_count": count_parameters(model),
        },
        checkpoint,
    )
    return {
        "checkpoint": str(checkpoint),
        "loss": history,
        "parameter_count": count_parameters(model),
        "device": str(target_device),
        "backbone": backbone,
        "is_synthetic": all(clip.source.is_synthetic for clip in training_clips),
        "evidence_state": "tested_offline",
    }


def load_checkpoint(path: Path, device: str = "cpu") -> nn.Module:
    """Load a policy entirely offline and place both weights and module on device."""

    target_device = torch.device(device)
    blob = torch.load(Path(path), map_location=target_device, weights_only=False)
    model = build_policy(
        backbone=blob["backbone"],
        in_frames=blob["in_frames"],
        image_size=blob["image_size"],
    ).to(target_device)
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model
