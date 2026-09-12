"""Causal camera history with modality, sequence, and monotonic-time checks.

A viewpoint/modality switch requires an explicit reset. Large gaps rewarm the
buffer. Optional fixed-period sampling selects past frames only (never future).
"""
from __future__ import annotations
from collections import deque
import numpy as np
from caferoomba.perception.camera import FrameSet
from caferoomba.perception.preprocessing import rgb_tensor


class CausalFrameBuffer:
    def __init__(self, *, frame_count: int, size: int, sample_period_ms: int = 0,
                 max_gap_ms: int = 500) -> None:
        if min(frame_count, size, max_gap_ms) < 1 or sample_period_ms < 0:
            raise ValueError("invalid buffer dimensions/timing")
        self.frame_count, self.size = frame_count, size
        self.period, self.max_gap_ms = sample_period_ms, max_gap_ms
        self._frames = deque(maxlen=max(frame_count, frame_count * 64))
        self.latest_t_ms = self._identity = self._last_id = None

    def reset(self) -> None:
        self._frames.clear()
        self.latest_t_ms = self._identity = self._last_id = None

    def push(self, sample: FrameSet) -> None:
        if sample.modality != "rgb":
            raise ValueError("RGB policy refuses infrared/depth; record diagnostics separately")
        identity = (sample.source, sample.modality)
        if self._identity is not None and identity != self._identity:
            raise ValueError("camera viewpoint changed; reset buffer before resuming")
        if self.latest_t_ms is not None and sample.t_ms < self.latest_t_ms:
            raise ValueError("camera clock moved backwards")
        if sample.frame_id is not None and self._last_id is not None:
            if sample.frame_id <= self._last_id:
                raise ValueError("duplicate/out-of-order camera frame")
        if self.latest_t_ms is not None and sample.t_ms - self.latest_t_ms > self.max_gap_ms:
            self._frames.clear()
        self._frames.append((sample.t_ms, rgb_tensor(sample.color, self.size)))
        self.latest_t_ms, self._identity, self._last_id = sample.t_ms, identity, sample.frame_id

    def _selection(self):
        rows = list(self._frames)
        if len(rows) < self.frame_count:
            return []
        if not self.period:
            return rows[-self.frame_count:]
        end = rows[-1][0]
        selected = []
        for target in range(end - (self.frame_count - 1) * self.period, end + 1, self.period):
            candidates = [row for row in rows if row[0] <= target]
            if not candidates or target - candidates[-1][0] > self.max_gap_ms:
                return []
            selected.append(candidates[-1])
        return selected

    def ready(self) -> bool:
        return len(self._selection()) == self.frame_count

    def stack(self) -> np.ndarray:
        selected = self._selection()
        if len(selected) != self.frame_count:
            raise RuntimeError("causal buffer is not full")
        return np.stack([row[1] for row in selected], axis=0)[None, ...]

    def observation_age_ms(self, now_ms: int) -> int | None:
        if self.latest_t_ms is None or self.latest_t_ms > now_ms:
            return None
        return now_ms - self.latest_t_ms
