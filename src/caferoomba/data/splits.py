"""Split by whole runs. Neighboring frames from one run stay together."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from caferoomba.schemas import ClipRecord


class SplitError(ValueError):
    pass


def assign_run_splits(
    clips: list[ClipRecord],
    *,
    seed: str = "caferoomba-splits-v1",
    train_ratio: float = 0.5,
    val_ratio: float = 0.25,
) -> dict[str, str]:
    runs = sorted({clip.run_id for clip in clips})
    if len(runs) < 3:
        raise SplitError(
            f"need at least 3 independent runs for train/val/test, found {len(runs)}"
        )
    ranked = sorted(
        runs,
        key=lambda run_id: hashlib.sha256(f"{seed}:{run_id}".encode()).hexdigest(),
    )
    n_train = max(1, int(len(ranked) * train_ratio))
    n_val = max(1, int(len(ranked) * val_ratio))
    if n_train + n_val >= len(ranked):
        n_train = max(1, len(ranked) - 2)
        n_val = 1
    mapping: dict[str, str] = {}
    for index, run_id in enumerate(ranked):
        if index < n_train:
            mapping[run_id] = "train"
        elif index < n_train + n_val:
            mapping[run_id] = "val"
        else:
            mapping[run_id] = "test"
    if len(set(mapping.values())) < 3:
        raise SplitError("hash split collapsed; add more independent runs")
    return mapping


def apply_splits(clips: list[ClipRecord], mapping: dict[str, str]) -> list[ClipRecord]:
    grouped: dict[str, list[str]] = defaultdict(list)
    updated: list[ClipRecord] = []
    for clip in clips:
        split = mapping[clip.run_id]
        grouped[split].append(clip.clip_id)
        updated.append(clip.model_copy(update={"split": split}))
    return updated


def detect_split_leakage(clips: list[ClipRecord]) -> list[str]:
    owners: dict[str, set[str]] = defaultdict(set)
    for clip in clips:
        if clip.split:
            owners[clip.run_id].add(clip.split)
    return [run_id for run_id, splits in owners.items() if len(splits) > 1]
