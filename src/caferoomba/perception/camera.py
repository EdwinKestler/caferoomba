"""CameraSource protocol. Implementations must not open devices in __init__."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class FrameSet:
    """One camera sample. ``depth`` is omitted when the sensor has none."""

    color: np.ndarray  # H, W, 3 uint8 RGB
    t_ms: int
    source: str
    depth: np.ndarray | None = None


class CameraSource(Protocol):
    name: str

    def open(self) -> None:
        """Acquire the device. Safe to call once."""

    def read(self) -> FrameSet:
        """Return the latest frame or raise if closed/failed."""

    def close(self) -> None:
        """Release the device. Idempotent."""

    def is_open(self) -> bool: ...
