"""A stalled native camera must not keep the portable runtime alive."""
import time

import pytest

from caferoomba.perception.process import ProcessCamera


class StalledCamera:
    name = "stall-test"

    def open(self):
        pass

    def read(self):
        time.sleep(30)

    def close(self):
        pass


class FailedCamera(StalledCamera):
    def open(self):
        raise PermissionError("test camera permission denied")


def test_native_startup_error_is_preserved():
    camera = ProcessCamera(FailedCamera())
    with pytest.raises(RuntimeError, match="PermissionError: test camera permission denied"):
        camera.open()
    assert not camera.is_open()


def test_stalled_camera_process_is_reaped_on_startup_timeout():
    camera = ProcessCamera(StalledCamera(), timeout_s=.2)
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        camera.open()
    assert not camera.is_open()
    assert time.monotonic() - started < 5
    camera.close()
