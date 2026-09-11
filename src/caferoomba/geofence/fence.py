"""PR1 fence: optional always-ok, or fail-closed when required but unloaded."""

from __future__ import annotations


class Fence:
    def __init__(self, *, required: bool) -> None:
        self.required = required

    def allows(self, latitude_deg: float | None, longitude_deg: float | None) -> bool:
        if not self.required:
            return True
        if latitude_deg is None or longitude_deg is None:
            return False
        return False  # PR2 loads the polygon; required+no-polygon is fail-closed
