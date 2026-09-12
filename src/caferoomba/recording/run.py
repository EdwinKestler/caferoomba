"""Asynchronous local recording with bounded queue and explicit dropped counts.

RGB/IR images and raw metric-scaled depth remain separate. A shadow prediction
is never relabeled as a human demonstration. No cloud credentials are read.
"""
from __future__ import annotations

import json
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image


class RunRecorder:
    def __init__(self, root: Path, *, save_frames=False, capacity=32):
        self.root, self.save_frames = root, save_frames
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
        self.path = root / self.run_id
        self._queue = queue.Queue(maxsize=capacity)
        self._stop = threading.Event()
        self._thread = None
        self.dropped = self.written = 0
        self.error = None
        self._lifecycle = threading.Lock()
        self._accepting = False

    def open(self):
        if self._thread is not None:
            raise RuntimeError("recorder is single-use")
        self.path.mkdir(parents=True, exist_ok=False)
        self._thread = threading.Thread(
            target=self._worker, name="caferoomba-recorder", daemon=True
        )
        self._thread.start()
        self._accepting = True

    def record(self, row: dict, sample=None):
        with self._lifecycle:
            if not self._accepting:
                raise RuntimeError("recording requires an open recorder")
            if self.error:
                raise RuntimeError(f"recording failed: {self.error}")
            try:
                self._queue.put_nowait((dict(row), sample if self.save_frames else None))
            except queue.Full:
                self.dropped += 1

    def _worker(self):
        try:
            with (self.path / "observations.jsonl").open("x", encoding="utf-8") as log:
                while not self._stop.is_set() or not self._queue.empty():
                    try:
                        row, sample = self._queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if sample is not None:
                        name = f"frame_{self.written:07d}"
                        image = name + "_" + sample.modality + ".png"
                        Image.fromarray(sample.color).save(self.path / image)
                        row["image_path"] = image
                        if sample.depth is not None:
                            depth = name + "_depth.npy"
                            np.save(self.path / depth, sample.depth, allow_pickle=False)
                            row["depth_path"] = depth
                            row["depth_scale_m"] = sample.depth_scale_m
                        row["calibration"] = sample.calibration
                    row["run_id"] = self.run_id
                    row["label_source"] = None  # Raw controls need explicit mapping/review.
                    log.write(json.dumps(row, allow_nan=False) + "\n")
                    log.flush()
                    self.written += 1
        except Exception as exc:
            self.error = str(exc)

    def close(self, *, summary=None):
        with self._lifecycle:
            self._accepting = False
            self._stop.set()
        if self._thread is None:
            return
        if self._thread:
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                raise RuntimeError("recorder did not drain before deadline")
        manifest = {"schema": "caferoomba.shadow-run.v1", "run_id": self.run_id,
                    "complete": self.error is None and self.dropped == 0, "written": self.written,
                    "dropped": self.dropped, "error": self.error,
                    "commands_sent": 0, "summary": summary or {}}
        (self.path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if self.error:
            raise RuntimeError(self.error)
