"""Serviced patches with spatial tolerance. Exact GPS equality is not required."""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class PatchVisit:
    patch_id: str
    x_m: float
    y_m: float
    visited_at_s: float

    def __post_init__(self):
        if not self.patch_id or not all(math.isfinite(v) for v in
                                       (self.x_m, self.y_m, self.visited_at_s)):
            raise ValueError("patch identity and coordinates/time must be valid")


class PatchStore:
    def __init__(self, path: Path, *, radius_m: float = 2.0) -> None:
        if not math.isfinite(radius_m) or radius_m <= 0:
            raise ValueError("patch radius must be finite and positive")
        self.path = path
        self.radius_m = radius_m
        self.visits: list[PatchVisit] = []
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.visits = [PatchVisit(**row) for row in raw]

    def _distance(self, x: float, y: float, other: PatchVisit) -> float:
        return math.hypot(x - other.x_m, y - other.y_m)

    def seen(self, x: float, y: float) -> PatchVisit | None:
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("patch coordinates must be finite")
        for visit in self.visits:
            if self._distance(x, y, visit) <= self.radius_m:
                return visit
        return None

    def record(self, patch_id: str, x: float, y: float, visited_at_s: float) -> PatchVisit:
        existing = self.seen(x, y)
        if existing:
            return existing
        visit = PatchVisit(patch_id=patch_id, x_m=x, y_m=y, visited_at_s=visited_at_s)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        updated = [*self.visits, visit]
        payload = json.dumps([asdict(item) for item in updated], indent=2, allow_nan=False)
        # Single-writer store: publish a complete file before changing in-memory state.
        fd, temporary = tempfile.mkstemp(prefix=".patches-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.visits = updated
        return visit
