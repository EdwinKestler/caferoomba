"""Hardware-free USB webcam and RealSense selection tests."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

from caferoomba.perception.realsense import RealSenseCamera
from caferoomba.perception.usb import UsbCamera


class FakeCapture:
    def __init__(self, *, opened=True, frame=None, read_ok=True):
        self.opened = opened
        self.frame = frame
        self.read_ok = read_ok
        self.released = False
        self.properties = []

    def isOpened(self):
        return self.opened and not self.released

    def set(self, prop, value):
        self.properties.append((prop, value))
        return True

    def read(self):
        return self.read_ok, self.frame

    def release(self):
        self.released = True


def fake_cv2(capture, calls):
    def video_capture(device, backend):
        calls.append((device, backend))
        return capture

    return SimpleNamespace(
        CAP_V4L2=200,
        CAP_PROP_FRAME_WIDTH=3,
        CAP_PROP_FRAME_HEIGHT=4,
        CAP_PROP_FPS=5,
        CAP_PROP_BUFFERSIZE=38,
        CAP_PROP_READ_TIMEOUT_MSEC=54,
        VideoCapture=video_capture,
    )


def test_usb_camera_is_lazy_uses_stable_v4l2_path_and_returns_rgb(monkeypatch):
    monkeypatch.delitem(sys.modules, "cv2", raising=False)
    camera = UsbCamera(
        device="/dev/v4l/by-id/usb-cafe-camera-video-index0",
        width=320,
        height=240,
        fps=30,
        timeout_ms=275,
    )
    assert "cv2" not in sys.modules

    bgr = np.array([[[1, 2, 3], [4, 5, 6]]], dtype=np.uint8)
    capture, calls = FakeCapture(frame=bgr), []
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2(capture, calls))
    monkeypatch.setattr("caferoomba.perception.usb.time.monotonic_ns", lambda: 12_345_678_999)

    camera.open()
    sample = camera.read()

    assert calls == [("/dev/v4l/by-id/usb-cafe-camera-video-index0", 200)]
    assert capture.properties == [(3, 320), (4, 240), (5, 30), (38, 1)]
    assert sample.color.tolist() == [[[3, 2, 1], [6, 5, 4]]]
    assert sample.color.flags.c_contiguous
    assert sample.source == "usb" and sample.modality == "rgb" and sample.frame_id == 1
    assert sample.t_ms == sample.received_at_ms == 12_345
    assert sample.timestamp_quality == "host_receipt_only"
    assert sample.clock_domain == "host_monotonic" and sample.native_timestamp_ms is None
    assert sample.depth is None and sample.depth_scale_m is None
    assert camera.is_open()

    camera.close()
    camera.close()
    assert capture.released and not camera.is_open()


def test_usb_camera_releases_failed_open_and_reports_read_errors(monkeypatch):
    failed, calls = FakeCapture(opened=False), []
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2(failed, calls))
    camera = UsbCamera(device="/dev/v4l/by-path/platform-test-video-index0")
    with pytest.raises(RuntimeError, match="unable to open"):
        camera.open()
    assert failed.released and not camera.is_open()

    empty, calls = FakeCapture(frame=None, read_ok=False), []
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2(empty, calls))
    camera.open()
    with pytest.raises(RuntimeError, match="returned no frame"):
        camera.read()
    camera.close()
    assert empty.released


def test_usb_camera_rejects_invalid_frames_and_read_before_open(monkeypatch):
    camera = UsbCamera(device="/dev/video-test")
    with pytest.raises(RuntimeError, match="before open"):
        camera.read()

    grayscale = np.zeros((4, 4), dtype=np.uint8)
    capture, calls = FakeCapture(frame=grayscale), []
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2(capture, calls))
    camera.open()
    with pytest.raises(RuntimeError, match="three-channel"):
        camera.read()
    camera.close()


def test_realsense_serial_is_bound_on_every_attempt(monkeypatch):
    configs = []

    class Config:
        def __init__(self):
            self.device = None
            configs.append(self)

        def enable_device(self, serial):
            self.device = serial

        def enable_stream(self, *args):
            pass

    class Pipeline:
        def start(self, config):
            raise RuntimeError("synthetic start failure")

    fake_rs = SimpleNamespace(
        stream=SimpleNamespace(color=1, depth=2, infrared=3),
        format=SimpleNamespace(bgr8=10, z16=11, y8=12),
        pipeline=Pipeline,
        config=Config,
    )
    monkeypatch.setitem(sys.modules, "pyrealsense2", fake_rs)

    camera = RealSenseCamera(serial_number="  D415-SERIAL  ")
    with pytest.raises(RuntimeError, match="RealSense unavailable"):
        camera.open()
    assert [config.device for config in configs] == ["D415-SERIAL"]
    assert not camera.is_open()


def test_realsense_rejects_blank_serial_without_loading_sdk(monkeypatch):
    monkeypatch.delitem(sys.modules, "pyrealsense2", raising=False)
    with pytest.raises(ValueError, match="must not be blank"):
        RealSenseCamera(serial_number="  ")
    assert "pyrealsense2" not in sys.modules
