"""Causal frame stacks. Future frames never enter the tensor."""

from __future__ import annotations

import numpy as np
from PIL import Image

from caferoomba.data.clips import assert_causal
from caferoomba.schemas import CLASS_ORDER, ClipRecord


def load_clip_stack(clip: ClipRecord, *, size: int) -> np.ndarray:
    assert_causal(clip.window)
    frames = []
    for path in clip.frame_paths:
        image = Image.open(path).convert("RGB").resize((size, size))
        array = np.asarray(image, dtype=np.float32) / 255.0
        frames.append(array.transpose(2, 0, 1))
    stack = np.stack(frames, axis=0)
    if stack.shape[0] != clip.window.frame_count:
        raise ValueError("frame stack does not match the causal window")
    return stack


def action_index(clip: ClipRecord) -> int:
    return CLASS_ORDER.index(clip.source.action.value)


def iter_examples(clips: list[ClipRecord], *, size: int, split: str | None = None):
    for clip in clips:
        if split and clip.split != split:
            continue
        yield {
            "frames": load_clip_stack(clip, size=size),
            "action": action_index(clip),
            "turn180": float(clip.source.turn180_onset),
            "clip_id": clip.clip_id,
            "run_id": clip.run_id,
            "is_synthetic": clip.source.is_synthetic,
        }
