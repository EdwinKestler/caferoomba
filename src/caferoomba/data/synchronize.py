"""Explicit clock-domain checks. Frame-index/FPS is not used as a PTS substitute."""

from __future__ import annotations


class SyncError(ValueError):
    """Raised when operator and video clocks disagree beyond tolerance."""


def check_sync(
    *,
    video_timestamp_ms: int,
    operator_timestamp_ms: int | None,
    tolerance_ms: int,
) -> None:
    if operator_timestamp_ms is None:
        return
    delta = abs(int(video_timestamp_ms) - int(operator_timestamp_ms))
    if delta > int(tolerance_ms):
        raise SyncError(
            f"clock mismatch {delta}ms exceeds tolerance {tolerance_ms}ms "
            "(operator vs video PTS)"
        )
