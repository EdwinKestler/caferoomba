"""Portable camera contract; construction must not acquire USB/CSI devices.

`t_ms` uses the host monotonic domain. timestamp_quality describes whether it
is capture time or only a receipt/estimated time. No precision is invented.
Depth is raw sensor units; depth_scale_m is required to interpret metres.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class FrameSet:
    color: np.ndarray
    t_ms: int
    source: str
    depth: np.ndarray | None = None
    frame_id: int | None = None
    modality: str = "rgb"
    received_at_ms: int | None = None
    native_timestamp_ms: float | None = None
    clock_domain: str = "host_monotonic"
    timestamp_quality: str = "provided_monotonic"
    depth_scale_m: float | None = None
    calibration: dict | None = None
    is_synthetic: bool = False


class CameraSource(Protocol):
    name: str
    def open(self) -> None: ...
    def read(self) -> FrameSet: ...
    def close(self) -> None: ...
    def is_open(self) -> bool: ...
