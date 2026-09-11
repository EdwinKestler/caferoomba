"""Causal clip windows that end at the decision timestamp."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from caferoomba.schemas import ClipRecord, ClipWindow, DemonstrationRecord


class ClipError(ValueError):
    pass


def causal_window(
    decision_timestamp_ms: int,
    *,
    frame_count: int,
    period_ms: int,
) -> ClipWindow:
    if frame_count < 1 or period_ms <= 0:
        raise ClipError("frame_count >= 1 and period_ms > 0 required")
    start = decision_timestamp_ms - (frame_count - 1) * period_ms
    if start < 0:
        raise ClipError("causal window would start before t=0")
    return ClipWindow(
        start_timestamp_ms=start,
        end_timestamp_ms=decision_timestamp_ms,
        decision_timestamp_ms=decision_timestamp_ms,
        frame_count=frame_count,
        includes_future_frames=False,
    )


def assert_causal(window: ClipWindow) -> None:
    if window.end_timestamp_ms != window.decision_timestamp_ms:
        raise ClipError("clip must end at the decision timestamp")
    if window.includes_future_frames:
        raise ClipError("future frames are not allowed in policy inputs")
    if window.start_timestamp_ms > window.end_timestamp_ms:
        raise ClipError("invalid clip window")


def write_synthetic_frames(
    directory: Path,
    *,
    action: str,
    frame_count: int,
    size: int = 64,
) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    colors = {
        "LEFT": (40, 120, 220),
        "RIGHT": (220, 80, 40),
        "STRAIGHT": (40, 180, 80),
        "STOP": (20, 20, 20),
    }
    rgb = colors.get(action, (120, 120, 120))
    paths: list[str] = []
    for index in range(frame_count):
        image = Image.new("RGB", (size, size), rgb)
        draw = ImageDraw.Draw(image)
        draw.rectangle((4, 4, 12, size - 4), fill=(255, 255, 255))
        draw.text((16, 24), f"{action[:1]}{index}", fill=(255, 255, 255))
        path = directory / f"frame_{index:03d}.png"
        image.save(path)
        paths.append(str(path))
    return paths


def clip_from_record(
    record: DemonstrationRecord,
    frame_paths: list[str],
    *,
    frame_count: int,
    period_ms: int,
) -> ClipRecord:
    window = causal_window(
        record.decision_timestamp_ms, frame_count=frame_count, period_ms=period_ms
    )
    assert_causal(window)
    if len(frame_paths) != frame_count:
        raise ClipError(f"expected {frame_count} frames, got {len(frame_paths)}")
    return ClipRecord(
        clip_id=f"{record.run_id}:{record.decision_timestamp_ms}",
        run_id=record.run_id,
        source=record,
        window=window,
        frame_paths=frame_paths,
    )
