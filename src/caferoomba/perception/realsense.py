"""Bounded RealSense RGB/depth acquisition; IR is a separate diagnostic modality.

Import the SDK in open(), preserve raw Z16 depth and scale. Hardware-clock
frames disclose host-receipt-only timing; this is not verified capture timing.
"""
from __future__ import annotations

import time

import numpy as np

from caferoomba.perception.camera import FrameSet


class RealSenseCamera:
    name = "realsense"

    def __init__(self, *, width=640, height=480, fps=15, timeout_ms=300,
                 allow_infrared_diagnostics=False, serial_number=None):
        if serial_number is not None and not str(serial_number).strip():
            raise ValueError("RealSense serial number must not be blank")
        self.width, self.height, self.fps = width, height, fps
        self.timeout_ms = timeout_ms
        self.allow_infrared = allow_infrared_diagnostics
        self.serial_number = str(serial_number).strip() if serial_number is not None else None
        self._pipeline = self._rs = self._first = None
        self.usb_type, self.stream = "unknown", "closed"
        self.depth_scale_m = None

    def _sample(self, frames):
        frame, modality = frames.get_color_frame(), "rgb"
        if not frame:
            frame, modality = frames.get_infrared_frame(), "infrared"
        if not frame:
            raise RuntimeError("RealSense frameset has no image")
        array = np.asanyarray(frame.get_data())
        rgb = array[:, :, ::-1].copy() if modality == "rgb" else np.repeat(array[..., None], 3, 2)
        received = int(time.monotonic() * 1000)
        stamp = float(frame.get_timestamp())
        domain = str(frame.get_frame_timestamp_domain()).split(".")[-1]
        quality, captured = "host_receipt_only", received
        if domain in {"system_time", "global_time"}:
            age = time.time() * 1000 - stamp
            if not np.isfinite(age) or age < -5:
                raise RuntimeError("invalid/future RealSense capture timestamp")
            captured = received - int(max(0, age))
            quality = "device_global_aligned"
        depth_frame = frames.get_depth_frame()
        intr = frame.profile.as_video_stream_profile().get_intrinsics()
        calibration = {"width": intr.width, "height": intr.height, "fx": intr.fx,
                       "fy": intr.fy, "ppx": intr.ppx, "ppy": intr.ppy,
                       "coeffs": list(intr.coeffs), "model": str(intr.model),
                       "depth_aligned_to_image": False}
        return FrameSet(color=rgb, depth=np.asanyarray(depth_frame.get_data()).copy()
                        if depth_frame else None, t_ms=captured, source="realsense",
                        frame_id=int(frame.get_frame_number()), modality=modality,
                        received_at_ms=received, native_timestamp_ms=stamp,
                        clock_domain=domain, timestamp_quality=quality,
                        depth_scale_m=self.depth_scale_m, calibration=calibration)

    def open(self):
        if self._pipeline is not None:
            raise RuntimeError("RealSense camera already open")
        import pyrealsense2 as rs
        self._rs = rs
        profiles = [("color+depth", [(rs.stream.color, self.width, self.height,
                                     rs.format.bgr8, self.fps),
                                    (rs.stream.depth, self.width, self.height,
                                     rs.format.z16, self.fps)])]
        if self.allow_infrared:
            profiles.append(("infrared+depth-diagnostic", [
                (rs.stream.infrared, 1, 480, 270, rs.format.y8, 6),
                (rs.stream.depth, 480, 270, rs.format.z16, 6)]))
        errors = []
        for name, streams in profiles:
            pipeline, cfg = rs.pipeline(), rs.config()
            if self.serial_number is not None:
                cfg.enable_device(self.serial_number)
            for spec in streams:
                cfg.enable_stream(*spec)
            started = False
            try:
                profile = pipeline.start(cfg)
                started = True
                device = profile.get_device()
                self.depth_scale_m = float(device.first_depth_sensor().get_depth_scale())
                self.usb_type = device.get_info(rs.camera_info.usb_type_descriptor)
                frames = pipeline.wait_for_frames(timeout_ms=2000)
                self.stream = name
                self._first = self._sample(frames)
                self._pipeline = pipeline
                return
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                if started:
                    pipeline.stop()
        raise RuntimeError("RealSense unavailable: " + "; ".join(errors))

    def read(self):
        if self._pipeline is None:
            raise RuntimeError("RealSenseCamera.read before open")
        if self._first is not None:
            sample, self._first = self._first, None
            return sample
        return self._sample(self._pipeline.wait_for_frames(timeout_ms=self.timeout_ms))

    def close(self):
        pipeline, self._pipeline = self._pipeline, None
        self._first = None
        if pipeline is not None:
            pipeline.stop()

    def is_open(self):
        return self._pipeline is not None
