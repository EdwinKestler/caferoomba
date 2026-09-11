"""Intel RealSense USB color (and depth if present).

On USB 2 the D415 RGB sensor often produces no frames; we then fall back to
infrared + depth (still a real still, not synthetic). Open only in ``open()``.
"""

from __future__ import annotations

import time

import numpy as np

from caferoomba.perception.camera import FrameSet


class RealSenseCamera:
    name = "realsense"

    def __init__(self, *, width: int = 640, height: int = 480, fps: int = 15) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.usb_type = "unknown"
        self.stream = "color"
        self._pipeline = None
        self._rs = None
        self._open = False

    def _from_frames(self, frames) -> FrameSet | None:
        color = frames.get_color_frame()
        if color:
            bgr = np.asanyarray(color.get_data())
            rgb = bgr[:, :, ::-1].copy() if bgr.ndim == 3 and bgr.shape[2] == 3 else bgr
            if rgb.ndim == 2:
                rgb = np.stack([rgb, rgb, rgb], axis=-1)
            depth = frames.get_depth_frame()
            return FrameSet(
                color=rgb,
                depth=np.asanyarray(depth.get_data()) if depth else None,
                t_ms=int(time.monotonic() * 1000),
                source=self.stream,
            )
        infrared = frames.get_infrared_frame()
        if infrared:
            gray = np.asanyarray(infrared.get_data())
            rgb = np.stack([gray, gray, gray], axis=-1)
            depth = frames.get_depth_frame()
            return FrameSet(
                color=rgb,
                depth=np.asanyarray(depth.get_data()) if depth else None,
                t_ms=int(time.monotonic() * 1000),
                source="infrared",
            )
        return None

    def _start(self, rs, streams: list[tuple]) -> object:
        pipeline = rs.pipeline()
        cfg = rs.config()
        for item in streams:
            cfg.enable_stream(*item)
        profile = pipeline.start(cfg)
        try:
            self.usb_type = profile.get_device().get_info(rs.camera_info.usb_type_descriptor)
        except Exception:
            self.usb_type = "unknown"
        return pipeline

    def _wait_sample(self, pipeline, attempts: int) -> FrameSet | None:
        last_error = None
        for _ in range(attempts):
            try:
                frames = pipeline.wait_for_frames(timeout_ms=2000)
                sample = self._from_frames(frames)
                if sample is not None:
                    return sample
            except RuntimeError as exc:
                last_error = exc
        self._last_error = last_error
        return None

    def open(self) -> None:
        try:
            import pyrealsense2 as rs
        except ImportError as exc:
            raise RuntimeError(
                "pyrealsense2 is not installed in this Python. "
                "Use .venv and: pip install pyrealsense2"
            ) from exc
        self._rs = rs
        profiles = [
            (
                "color+depth",
                [
                    (rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps),
                    (rs.stream.depth, self.width, self.height, rs.format.z16, self.fps),
                ],
            ),
            (
                "infrared+depth-usb2",
                [
                    (rs.stream.infrared, 1, 480, 270, rs.format.y8, 6),
                    (rs.stream.depth, 480, 270, rs.format.z16, 6),
                ],
            ),
        ]
        last_error: Exception | None = None
        for name, streams in profiles:
            pipeline = None
            try:
                pipeline = self._start(rs, streams)
                sample = self._wait_sample(pipeline, 8 if name.startswith("infrared") else 4)
                if sample is not None:
                    self._pipeline = pipeline
                    self._open = True
                    self.stream = name
                    return
                last_error = getattr(self, "_last_error", None)
            except Exception as exc:
                last_error = exc
            if pipeline is not None:
                try:
                    pipeline.stop()
                except Exception:
                    pass
        raise RuntimeError(
            f"RealSense produced no frames (usb={self.usb_type}): {last_error}. "
            "RGB needs USB 3; infrared/depth should work on USB 2."
        )

    def read(self) -> FrameSet:
        if not self._open or self._pipeline is None:
            raise RuntimeError("RealSenseCamera.read() before open()")
        sample = self._wait_sample(self._pipeline, 10)
        if sample is None:
            raise RuntimeError(f"RealSense produced no frame: {self._last_error}")
        return sample

    def close(self) -> None:
        if self._pipeline is not None:
            try:
                self._pipeline.stop()
            except Exception:
                pass
            self._pipeline = None
        self._open = False

    def is_open(self) -> bool:
        return self._open
