"""Clearly labeled synthetic demonstration data for CPU smoke tests."""

from __future__ import annotations

from pathlib import Path

from caferoomba.data.clips import clip_from_record, write_synthetic_frames
from caferoomba.data.splits import apply_splits, assign_run_splits
from caferoomba.schemas import ActionLabel, DemonstrationRecord, LabelSource, Viewpoint

ACTIONS = (
    (ActionLabel.STRAIGHT, False, None),
    (ActionLabel.LEFT, False, None),
    (ActionLabel.RIGHT, False, None),
    (ActionLabel.STOP, False, None),
    (ActionLabel.STRAIGHT, True, "left"),
    (ActionLabel.LEFT, True, "right"),
)


def build_synthetic_clips(root: Path, *, frame_count: int = 8, period_ms: int = 250) -> list:
    records = []
    clips = []
    for index, (action, turn, direction) in enumerate(ACTIONS):
        run_id = f"synthetic-run-{index:02d}"
        decision_ms = 2000
        record = DemonstrationRecord(
            run_id=run_id,
            patch_id=f"patch-{index}",
            viewpoint=Viewpoint.SYNTHETIC,
            time_base="pts",
            fps_nominal=4.0,
            operator_command=action.value,
            operator_timestamp_ms=decision_ms,
            decision_timestamp_ms=decision_ms,
            action=action,
            turn180_onset=turn,
            turn180_direction=direction,
            label_source=LabelSource.human,
            sync_quality="synthetic_exact",
            is_synthetic=True,
            notes="SYNTHETIC FIXTURE — not a real FPV demonstration",
        )
        frames = write_synthetic_frames(
            root / run_id, action=action.value, frame_count=frame_count
        )
        records.append(record)
        clips.append(
            clip_from_record(record, frames, frame_count=frame_count, period_ms=period_ms)
        )
    mapping = assign_run_splits(clips, train_ratio=0.5, val_ratio=0.17)
    return apply_splits(clips, mapping)
