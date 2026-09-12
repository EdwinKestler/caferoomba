"""Headless Jetson IMX219 via native Argus/GStreamer, without Python ABI mixing.

No shell and no import-time hardware access. RGB pipe reads have deadlines;
cleanup terminates only the child created by this object. Native plugins must
already be installed on the Jetson. This backend cannot be tested on x86.
"""
from __future__ import annotations

import os
import platform
import select
import shutil
import subprocess
import time

import numpy as np

from caferoomba.perception.camera import FrameSet


class Imx219Camera:
    name = "imx219"

    def __init__(self, *, sensor_id=0, width=640, height=480, fps=15, timeout_ms=300):
        self.sensor_id, self.width, self.height = sensor_id, width, height
        self.fps, self.timeout_ms = fps, timeout_ms
        self._process, self._sequence = None, 0

    def open(self):
        if platform.machine() not in {"aarch64", "arm64"}:
            raise RuntimeError("IMX219 CSI requires Jetson; use RealSense on this workstation")
        if self._process is not None:
            raise RuntimeError("CSI camera already open")
        executable = shutil.which("gst-launch-1.0")
        if not executable:
            raise RuntimeError("native GStreamer/Argus installation is required")
        command = [executable, "-q", "nvarguscamerasrc", f"sensor-id={self.sensor_id}",
                   "!", f"video/x-raw(memory:NVMM),width=1280,height=720,framerate={self.fps}/1",
                   "!", "nvvidconv", "!",
                   f"video/x-raw,format=RGBA,width={self.width},height={self.height}",
                   "!", "videoconvert", "!", "video/x-raw,format=RGB", "!",
                   "fdsink", "fd=1", "sync=false"]
        self._process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, bufsize=0)

    def read(self):
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("Imx219Camera.read before open")
        needed, data = self.width * self.height * 3, bytearray()
        deadline = time.monotonic() + self.timeout_ms / 1000
        while len(data) < needed:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self._process.stdout], [], [], remaining)[0]:
                raise TimeoutError("CSI frame deadline exceeded")
            chunk = os.read(self._process.stdout.fileno(), needed - len(data))
            if not chunk:
                raise RuntimeError("CSI pipeline exited before a complete RGB frame")
            data.extend(chunk)
        self._sequence += 1
        now = int(time.monotonic() * 1000)
        return FrameSet(np.frombuffer(data, np.uint8).reshape(self.height, self.width, 3).copy(),
                        now, "imx219", frame_id=self._sequence, received_at_ms=now,
                        timestamp_quality="host_receipt_only")

    def close(self):
        process, self._process = self._process, None
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            if process.stdout:
                process.stdout.close()

    def is_open(self):
        return self._process is not None and self._process.poll() is None
