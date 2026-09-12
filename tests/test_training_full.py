from __future__ import annotations

from pathlib import Path

import pytest
import torch

from caferoomba.data.clips import clip_from_record, write_synthetic_frames
from caferoomba.learning.evaluate import evaluate_clips
from caferoomba.learning.train import (
    _restore_rng,
    _rng_state,
    load_checkpoint,
    train_epochs,
    train_steps,
)
from caferoomba.schemas import ActionLabel, DemonstrationRecord, LabelSource, Viewpoint

DATASET_SHA256 = "a" * 64


def _clips(root: Path, *, train: int = 3, val: int = 1, test: int = 1) -> list:
    actions = list(ActionLabel)
    paths_by_action = {
        action: write_synthetic_frames(
            root / f"frames-{action.value.lower()}",
            action=action.value,
            frame_count=8,
            size=16,
        )
        for action in actions
    }
    clips = []
    index = 0
    for split, count in (("train", train), ("val", val), ("test", test)):
        for _ in range(count):
            action = actions[index % len(actions)]
            run_id = f"{split}-run-{index:03d}"
            record = DemonstrationRecord(
                run_id=run_id,
                viewpoint=Viewpoint.SYNTHETIC,
                decision_timestamp_ms=2000,
                action=action,
                turn180_onset=index % 3 == 0,
                label_source=LabelSource.human,
                is_synthetic=True,
            )
            clip = clip_from_record(
                record, paths_by_action[action], frame_count=8, period_ms=250
            )
            clips.append(clip.model_copy(update={"split": split}))
            index += 1
    return clips


def test_train_epochs_consumes_every_batch_without_reading_test(tmp_path):
    clips = _clips(tmp_path / "frames", train=10, val=2, test=1)
    missing_test = clips[-1].model_copy(
        update={"frame_paths": [str(tmp_path / f"missing-{index}.png") for index in range(8)]}
    )
    clips[-1] = missing_test

    report = train_epochs(
        clips,
        output_dir=tmp_path / "run",
        epochs=1,
        batch_size=4,
        image_size=16,
        dataset_sha256=DATASET_SHA256,
    )

    assert report["history"][0]["train_examples"] == 10
    assert report["history"][0]["train_batches"] == 3
    assert report["history"][0]["val_examples"] == 2
    assert Path(report["best_checkpoint"]).is_file()
    assert Path(report["last_checkpoint"]).is_file()
    blob = torch.load(report["last_checkpoint"], map_location="cpu", weights_only=False)
    assert blob["dataset_sha256"] == DATASET_SHA256
    assert blob["config"]["in_frames"] == 8
    assert blob["config"]["image_size"] == 16
    assert blob["optimizer_state_dict"]
    assert set(blob["rng_state"]) >= {"python", "numpy", "torch", "shuffle"}
    assert set(blob["split_fingerprints"]) == {"train", "val", "test"}


def test_train_steps_rejects_empty_train_instead_of_falling_back(tmp_path):
    clips = [clip.model_copy(update={"split": "val"}) for clip in _clips(tmp_path / "f")]
    with pytest.raises(ValueError, match="no training examples"):
        train_steps(clips, output_dir=tmp_path / "run", image_size=16)


def test_training_and_heldout_evaluation_reject_run_leakage(tmp_path):
    clips = _clips(tmp_path / "frames")
    clips[-2] = clips[-2].model_copy(update={"run_id": clips[0].run_id})
    with pytest.raises(ValueError, match="run leakage"):
        train_epochs(clips, output_dir=tmp_path / "run", image_size=16)

    model = torch.nn.Sequential()
    with pytest.raises(ValueError, match="run leakage"):
        evaluate_clips(model, clips, image_size=16, split="val")


def test_resume_matches_uninterrupted_training_and_rejects_config_change(tmp_path):
    clips = _clips(tmp_path / "frames", train=4, val=2, test=1)
    common = {
        "epochs": 2,
        "batch_size": 2,
        "lr": 1e-3,
        "image_size": 16,
        "seed": 7,
        "dataset_sha256": DATASET_SHA256,
    }
    uninterrupted = train_epochs(clips, output_dir=tmp_path / "full", **common)
    first = train_epochs(
        clips,
        output_dir=tmp_path / "resumed",
        epochs=1,
        batch_size=2,
        lr=1e-3,
        image_size=16,
        seed=7,
        dataset_sha256=DATASET_SHA256,
    )
    relocated_clips = _clips(tmp_path / "relocated-frames", train=4, val=2, test=1)
    resumed = train_epochs(
        relocated_clips,
        output_dir=tmp_path / "resumed",
        resume=Path(first["last_checkpoint"]),
        **common,
    )
    full_blob = torch.load(
        uninterrupted["last_checkpoint"], map_location="cpu", weights_only=False
    )
    resumed_blob = torch.load(resumed["last_checkpoint"], map_location="cpu", weights_only=False)
    assert resumed["history"] == uninterrupted["history"]
    for name, tensor in full_blob["state_dict"].items():
        assert torch.equal(tensor, resumed_blob["state_dict"][name]), name
    assert torch.equal(full_blob["rng_state"]["torch"], resumed_blob["rng_state"]["torch"])
    assert torch.equal(full_blob["rng_state"]["shuffle"], resumed_blob["rng_state"]["shuffle"])

    with pytest.raises(ValueError, match="resume config mismatch"):
        train_epochs(
            clips,
            output_dir=tmp_path / "bad-resume",
            epochs=3,
            batch_size=2,
            lr=2e-3,
            image_size=16,
            seed=7,
            dataset_sha256=DATASET_SHA256,
            resume=Path(resumed["last_checkpoint"]),
        )


def test_checkpoint_and_evaluation_honor_cpu_device(tmp_path):
    clips = _clips(tmp_path / "frames")
    report = train_epochs(clips, output_dir=tmp_path / "run", image_size=16)
    model = load_checkpoint(Path(report["checkpoint"]), device="cpu")
    assert next(model.parameters()).device.type == "cpu"

    metrics = evaluate_clips(model, clips, image_size=16, split="test", device="cpu")
    assert metrics["device"] == "cpu"
    assert metrics["split"] == "test"
    assert metrics["n"] == 1
    assert set(metrics["turn180"]) >= {"confusion", "precision", "recall", "f1"}


def test_nonfinite_configuration_and_logits_fail_closed(tmp_path):
    clips = _clips(tmp_path / "frames")
    with pytest.raises(ValueError, match="lr must be finite"):
        train_epochs(clips, output_dir=tmp_path / "run", image_size=16, lr=float("nan"))

    class NonFinitePolicy(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.anchor = torch.nn.Parameter(torch.zeros(()))

        def forward(self, frames):
            batch = frames.shape[0]
            return {
                "action_logits": torch.full((batch, 4), float("nan"), device=frames.device),
                "turn_logit": torch.zeros(batch, device=frames.device),
            }

    with pytest.raises(ValueError, match="non-finite logits"):
        evaluate_clips(NonFinitePolicy(), clips, image_size=16, split="test")


def test_cuda_resume_rng_is_converted_to_cpu(monkeypatch):
    generator = torch.Generator(device="cpu").manual_seed(3)
    state = _rng_state(generator)
    expected_cpu = torch.tensor([1, 2, 3], dtype=torch.uint8)

    class MappedCudaState:
        def cpu(self):
            return expected_cpu

    mapped_state = MappedCudaState()
    state["torch_cuda"] = [mapped_state]
    restored = []
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "set_rng_state_all", lambda values: restored.extend(values))

    _restore_rng(state, generator)

    assert restored == [expected_cpu]
    assert restored[0] is not mapped_state
