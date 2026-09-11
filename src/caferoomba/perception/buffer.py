"""Causal RGB stack: only frames already observed, oldest → newest."""

from __future__ import annotations

from collections import deque

import numpy as np
from PIL import Image

from caferoomba.perception.camera import FrameSet


class CausalFrameBuffer:
    """Holds the last ``frame_count`` color frames, resized to a square."""

    def __init__(self, *, frame_count: int, size: int) -> None:
        if frame_count < 1 or size < 1:
            raise ValueError("frame_count and size must be >= 1")
        self.frame_count = frame_count
        self.size = size
        self._frames: deque[np.ndarray] = deque(maxlen=frame_count)
        self.latest_t_ms: int | None = None

    def push(self, sample: FrameSet) -> None:
        image = Image.fromarray(sample.color).convert("RGB").resize((self.size, self.size))
        array = np.asarray(image, dtype=np.float32) / 255.0
        self._frames.append(array.transpose(2, 0, 1))
        self.latest_t_ms = sample.t_ms

    def ready(self) -> bool:
        return len(self._frames) == self.frame_count

    def stack(self) -> np.ndarray:
        """Return ``(1, T, C, H, W)`` or raise if not full."""
        if not self.ready():
            raise RuntimeError("causal buffer is not full")
        return np.stack(list(self._frames), axis=0)[None, ...]

    def observation_age_ms(self, now_ms: int) -> int | None:
        if self.latest_t_ms is None:
            return None
        return max(0, now_ms - self.latest_t_ms)
