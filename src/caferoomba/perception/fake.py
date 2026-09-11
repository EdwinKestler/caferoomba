"""Deterministic RGB frames for tests and dry-run. Never opens USB or CSI."""

from __future__ import annotations

import time

import numpy as np

from caferoomba.perception.camera import FrameSet


class FakeCamera:
    """Solid-color frames. ``open()`` is a no-op besides setting a flag."""

    name = "fake"

    def __init__(self, *, width: int = 64, height: int = 64) -> None:
        self.width = width
        self.height = height
        self._open = False
        self._index = 0

    def open(self) -> None:
        self._open = True

    def read(self) -> FrameSet:
        if not self._open:
            raise RuntimeError("FakeCamera.read() before open()")
        frame = np.full((self.height, self.width, 3), 40, dtype=np.uint8)
        frame[:, :, 1] = min(255, 80 + self._index % 100)
        self._index += 1
        return FrameSet(
            color=frame,
            t_ms=int(time.monotonic() * 1000),
            source=self.name,
        )

    def close(self) -> None:
        self._open = False

    def is_open(self) -> bool:
        return self._open
