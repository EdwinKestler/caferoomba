"""Portable Linux USB webcam capture through OpenCV's V4L2 backend.

Construction and module import do not import OpenCV or acquire a device. The
configured device string is passed through unchanged so callers can use a
stable ``/dev/v4l/by-id/...`` or ``/dev/v4l/by-path/...`` symlink.

V4L2/OpenCV does not expose a trustworthy sensor capture timestamp here. A
frame is therefore stamped in the host monotonic clock immediately after
``VideoCapture.read()`` returns and is labelled as host-receipt-only timing.
"""
from __future__ import annotations

import os
import time
from typing import Any

import numpy as np

from caferoomba.perception.camera import FrameSet


class UsbCamera:
    """OpenCV V4L2 RGB camera with explicit acquisition and cleanup."""

    name = "usb"

    def __init__(
        self,
        *,
        device: str | os.PathLike[str],
        width: int = 640,
        height: int = 480,
        fps: int = 15,
        timeout_ms: int = 300,
    ) -> None:
        try:
            device_path = os.fspath(device)
        except TypeError as exc:
            raise TypeError("USB camera device must be a filesystem path") from exc
        if not device_path:
            raise ValueError("USB camera device path must not be empty")
        if width <= 0 or height <= 0 or fps <= 0 or timeout_ms <= 0:
            raise ValueError("USB camera dimensions, fps, and timeout must be positive")

        self.device = device_path
        self.width, self.height, self.fps = int(width), int(height), int(fps)
        self.timeout_ms = int(timeout_ms)
        self._capture: Any | None = None
        self._sequence = 0

    def open(self) -> None:
        if self._capture is not None:
            raise RuntimeError("USB camera already open")
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "USB camera requires OpenCV; install the 'usb-camera' extra"
            ) from exc

        capture = None
        try:
            capture = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
            if not capture.isOpened():
                raise RuntimeError(f"unable to open USB camera {self.device!r} with V4L2")

            requested = (
                (cv2.CAP_PROP_FRAME_WIDTH, self.width),
                (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
                (cv2.CAP_PROP_FPS, self.fps),
            )
            for prop, value in requested:
                # Some UVC drivers negotiate a nearby mode and return False here.
                # The returned frame is authoritative, so unsupported hints are not fatal.
                capture.set(prop, value)
            if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # V4L2 has no supported OpenCV read deadline. ProcessCamera owns
            # acquisition and can terminate a stalled native driver at shutdown.
        except Exception:
            if capture is not None:
                try:
                    capture.release()
                except Exception:
                    pass  # Preserve the acquisition error that made cleanup necessary.
            raise

        self._capture = capture
        self._sequence = 0

    def read(self) -> FrameSet:
        capture = self._capture
        if capture is None:
            raise RuntimeError("UsbCamera.read before open")

        try:
            ok, bgr = capture.read()
        except Exception as exc:
            raise RuntimeError(f"USB camera {self.device!r} read failed") from exc
        received_at_ms = time.monotonic_ns() // 1_000_000
        if not ok or bgr is None:
            raise RuntimeError(f"USB camera {self.device!r} returned no frame")

        array = np.asarray(bgr)
        if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] != 3:
            raise RuntimeError(
                "USB camera must return an HWC uint8 three-channel BGR frame"
            )

        self._sequence += 1
        rgb = array[:, :, ::-1].copy()
        return FrameSet(
            color=rgb,
            t_ms=received_at_ms,
            source=self.name,
            depth=None,
            frame_id=self._sequence,
            modality="rgb",
            received_at_ms=received_at_ms,
            native_timestamp_ms=None,
            clock_domain="host_monotonic",
            timestamp_quality="host_receipt_only",
            depth_scale_m=None,
        )

    def close(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            capture.release()

    def is_open(self) -> bool:
        capture = self._capture
        if capture is None:
            return False
        try:
            return bool(capture.isOpened())
        except Exception:
            return False
