"""Isolate native UVC calls so a stalled driver cannot prevent runtime cleanup."""
from __future__ import annotations

import multiprocessing as mp
import queue
import time


def _capture(camera, frames, errors, stop):
    try:
        camera.open()
        while not stop.is_set():
            sample = camera.read()
            try:
                frames.put_nowait(sample)
            except queue.Full:
                try:
                    frames.get_nowait()
                except queue.Empty:
                    pass
                try:
                    frames.put_nowait(sample)
                except queue.Full:
                    pass
    except Exception as exc:
        errors.put(f"{type(exc).__name__}: {exc}")
    finally:
        camera.close()


class ProcessCamera:
    """One native owner, bounded latest-frame queue, explicit process teardown.

    Read polling never waits for a native UVC read. Missing frames age out in
    the supervisor. This does not invent device capture timestamps.
    """

    def __init__(self, camera, *, timeout_s=5.0):
        self.camera, self.name, self.timeout_s = camera, camera.name, timeout_s
        self._process = self._frames = self._errors = self._stop = None
        self._first = None

    def open(self):
        if self._process is not None:
            raise RuntimeError("camera process is single-use")
        context = mp.get_context("spawn")
        self._frames, self._errors = context.Queue(1), context.Queue(1)
        self._stop = context.Event()
        self._process = context.Process(
            target=_capture, args=(self.camera, self._frames, self._errors, self._stop),
            name="caferoomba-usb", daemon=True,
        )
        self._process.start()
        try:
            deadline = time.monotonic() + self.timeout_s
            while True:
                try:
                    error = self._errors.get_nowait()
                except queue.Empty:
                    error = None
                if error:
                    raise RuntimeError(error)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("USB camera startup deadline exceeded")
                try:
                    self._first = self._frames.get(timeout=min(.05, remaining))
                    break
                except queue.Empty:
                    continue
        except Exception:
            self.close()
            raise

    def read(self):
        if self._process is None:
            raise RuntimeError("camera process not opened")
        try:
            error = self._errors.get_nowait()
        except queue.Empty:
            error = None
        if error or not self._process.is_alive():
            raise RuntimeError(error or "camera process exited")
        if self._first is not None:
            sample, self._first = self._first, None
            return sample
        try:
            return self._frames.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        if self._process is None:
            return
        self._stop.set()
        self._process.join(timeout=.5)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1)
        if self._process.is_alive():
            self._process.kill()
            self._process.join(timeout=1)
        if self._process.is_alive():
            raise RuntimeError("USB camera process did not exit")
        for channel in (self._frames, self._errors):
            channel.cancel_join_thread()
            channel.close()

    def is_open(self):
        return self._process is not None and self._process.is_alive()
