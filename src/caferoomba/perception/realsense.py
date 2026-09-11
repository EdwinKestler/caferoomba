"""Intel RealSense USB color (and depth if present).

Open the device only in ``open()``. Requires ``pyrealsense2`` in the active
venv (``.venv``, not the pigpio rover env).
"""

from __future__ import annotations

import time

import numpy as np

from caferoomba.perception.camera import FrameSet


class RealSenseCamera:
    name = "realsense"

    def __init__(self, *, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self._pipeline = None
        self._open = False

    def open(self) -> None:
        try:
            import pyrealsense2 as rs
        except ImportError as exc:
            raise RuntimeError(
                "pyrealsense2 is not installed in this Python. "
                "Use .venv and: pip install pyrealsense2"
            ) from exc
        pipeline = rs.pipeline()
        cfg = rs.config()
        cfg.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, 30)
        try:
            cfg.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, 30)
        except Exception:
            pass
        pipeline.start(cfg)
        self._pipeline = pipeline
        self._rs = rs
        self._open = True

    def read(self) -> FrameSet:
        if not self._open or self._pipeline is None:
            raise RuntimeError("RealSenseCamera.read() before open()")
        frames = self._pipeline.wait_for_frames(timeout_ms=2000)
        color = frames.get_color_frame()
        if not color:
            raise RuntimeError("RealSense produced no color frame")
        bgr = np.asanyarray(color.get_data())
        rgb = bgr[:, :, ::-1].copy()
        depth_arr = None
        depth = frames.get_depth_frame()
        if depth:
            depth_arr = np.asanyarray(depth.get_data())
        return FrameSet(
            color=rgb,
            depth=depth_arr,
            t_ms=int(time.monotonic() * 1000),
            source=self.name,
        )

    def close(self) -> None:
        if self._pipeline is not None:
            self._pipeline.stop()
            self._pipeline = None
        self._open = False

    def is_open(self) -> bool:
        return self._open
