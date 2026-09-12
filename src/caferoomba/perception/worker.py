"""Single-owner camera worker with one latest sample, not a growing backlog.

Only the worker opens, reads, and closes its native camera. Native reads must
have deadlines. The runtime polls without waiting for USB or camera exposure.
"""
from __future__ import annotations

import threading


class LatestCamera:
    def __init__(self, camera, *, timeout_s=5.0):
        self.camera, self.timeout_s, self.name = camera, timeout_s, camera.name
        self._stop, self._ready = threading.Event(), threading.Event()
        self._lock = threading.Lock()
        self._sample = self._error = self._thread = None
        self._last_delivered = None

    def _run(self):
        try:
            self.camera.open()
            while not self._stop.is_set():
                sample = self.camera.read()
                with self._lock:
                    self._sample = sample
                self._ready.set()
        except Exception as exc:
            self._error = exc
            self._ready.set()
        finally:
            try:
                self.camera.close()
            except Exception as exc:
                self._error = self._error or exc

    def open(self):
        if self._thread is not None:
            raise RuntimeError("camera worker already started")
        self._thread = threading.Thread(target=self._run, name="caferoomba-camera", daemon=True)
        self._thread.start()
        if not self._ready.wait(self.timeout_s):
            self._stop.set()
            raise TimeoutError("camera startup deadline exceeded")
        if self._error:
            raise RuntimeError(f"camera acquisition failed: {self._error}") from self._error

    def read(self):
        if self._error:
            raise RuntimeError(f"camera acquisition failed: {self._error}") from self._error
        with self._lock:
            sample = self._sample
        if sample is None:
            return None
        identity = (sample.source, sample.frame_id, sample.t_ms)
        if identity == self._last_delivered:
            return None  # Age keeps increasing; never relabel an old frame as new.
        self._last_delivered = identity
        return sample

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(self.timeout_s)
            if self._thread.is_alive():
                raise RuntimeError("camera worker did not stop; native driver is stalled")

    def is_open(self):
        return self._thread is not None and self._thread.is_alive() and self._error is None
