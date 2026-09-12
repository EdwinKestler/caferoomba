"""Software-only checks for real-data gates; generated videos are not robot evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from caferoomba.data.prepare import (
    PrepareError,
    _select_frames,
    load_prepared_dataset,
    prepare_dataset,
)

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg and ffprobe are required",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_video(path: Path, color: str) -> None:
    """Generate a tiny 10 fps source whose non-grid PTS selections are observable."""

    path.parent.mkdir(parents=True)
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=32x24:r=10:d=3",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-frames:v",
            "30",
            "-y",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _reviewed_rows(media_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, color in enumerate(("red", "green", "blue"), start=1):
        video = media_root / f"run-{index}" / "video.mp4"
        _make_video(video, color)
        rows.append(
            {
                "schema_version": "caferoomba.labels.v1",
                "run_id": f"run-{index}",
                "session_id": f"session-{index}",
                "decision_timestamp_ms": 2000,
                "window_start_ms": 1250,
                "window_end_ms": 2000,
                "clip_path": f"run-{index}/clip.mp4",
                "video_path": video.relative_to(media_root).as_posix(),
                "video_sha256": _sha256(video),
                "viewpoint": "FPV",
                "action": ("LEFT", "STRAIGHT", "RIGHT")[index - 1],
                "turn180_onset": index == 1,
                "turn180_direction": "LEFT" if index == 1 else None,
                "label_source": "human",
                "reviewer": "test-reviewer",
                "status": "reviewed",
                "is_synthetic": False,
            }
        )
    return rows


def _write_labels(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_prepare_uses_actual_pts_and_loads_after_dataset_move(tmp_path: Path) -> None:
    media_root = tmp_path / "workspace"
    media_root.mkdir()
    rows = _reviewed_rows(media_root)
    labels = tmp_path / "labels.reviewed.jsonl"
    _write_labels(labels, rows)

    report = prepare_dataset(
        labels,
        media_root,
        tmp_path / "prepared",
        frame_count=4,
        period_ms=250,
        max_frame_age_ms=100,
    )
    assert report["clip_count"] == 3
    assert report["split_counts"] == {"train": 1, "val": 1, "test": 1}
    assert report["config"]["frame_count"] == 4

    manifest_path = Path(report["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["dataset_sha256"] == report["dataset_sha256"]
    assert all(not Path(source["path"]).is_absolute() for source in manifest["sources"])
    for entry in manifest["clips"]:
        assert all(not Path(path).is_absolute() for path in entry["record"]["frame_paths"])
        assert [frame["requested_timestamp_ms"] for frame in entry["frames"]] == [
            1250,
            1500,
            1750,
            2000,
        ]
        assert [frame["actual_pts_ms"] for frame in entry["frames"]] == [
            1200,
            1500,
            1700,
            2000,
        ]
        assert all(
            frame["actual_pts_ms"] <= frame["requested_timestamp_ms"]
            for frame in entry["frames"]
        )

    moved = tmp_path / "new-mount" / "dataset"
    moved.parent.mkdir()
    manifest_path.parent.rename(moved)
    clips = load_prepared_dataset(moved / "manifest.json")
    assert len(clips) == 3
    assert {clip.split for clip in clips} == {"train", "val", "test"}
    assert all(Path(path).is_absolute() for clip in clips for path in clip.frame_paths)

    moved_manifest = moved / "manifest.json"
    original_manifest = moved_manifest.read_text(encoding="utf-8")
    tampered = json.loads(original_manifest)
    tampered["config"]["period_ms"] = 251
    moved_manifest.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(PrepareError, match="manifest digest mismatch"):
        load_prepared_dataset(moved_manifest)
    moved_manifest.write_text(original_manifest, encoding="utf-8")

    Path(clips[0].frame_paths[0]).write_bytes(b"corrupt")
    with pytest.raises(PrepareError, match="frame hash mismatch"):
        load_prepared_dataset(moved / "manifest.json")


def test_pts_selection_never_uses_future_and_rejects_stale_frame() -> None:
    pts = [
        (Decimal(1000), "1.000000", 10),
        (Decimal(1300), "1.300000", 11),
    ]
    selected = _select_frames(pts, [1250], max_frame_age_ms=300)
    assert selected == [(Decimal(1000), "1.000000", 10, 1250)]
    with pytest.raises(PrepareError, match="250ms old"):
        _select_frames(pts, [1250], max_frame_age_ms=100)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("status", "unlabeled", "status must be reviewed"),
        ("viewpoint", "EXTERNAL", "only viewpoint=FPV"),
        ("label_source", "teacher_suggestion", "label_source must be human"),
        ("reviewer", None, "human reviewer is required"),
        ("is_synthetic", True, "is_synthetic=false"),
        ("turn180_onset", None, "explicit boolean"),
    ],
)
def test_prepare_rejects_non_human_or_incomplete_draft_labels(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    rows = []
    for index in range(3):
        row: dict[str, object] = {
            "schema_version": "caferoomba.labels.v1",
            "run_id": f"run-{index}",
            "decision_timestamp_ms": 1000,
            "window_start_ms": 0,
            "window_end_ms": 1000,
            "video_path": f"run-{index}/video.mp4",
            "video_sha256": f"{index + 1:064x}",
            "viewpoint": "FPV",
            "action": "STOP",
            "turn180_onset": False,
            "label_source": "human",
            "reviewer": "reviewer",
            "status": "reviewed",
            "is_synthetic": False,
        }
        row[field] = value
        rows.append(row)
    labels = media_root / "labels.jsonl"
    _write_labels(labels, rows)
    with pytest.raises(PrepareError, match=message):
        prepare_dataset(labels, media_root, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_prepare_accepts_explicit_reviewed_canonical_records(tmp_path: Path) -> None:
    media_root = tmp_path / "workspace"
    media_root.mkdir()
    rows = _reviewed_rows(media_root)
    for row in rows:
        row["schema_version"] = "caferoomba.record.v1"
        row.pop("window_start_ms")
        row.pop("window_end_ms")
        row.pop("clip_path")
    labels = tmp_path / "canonical.jsonl"
    _write_labels(labels, rows)
    report = prepare_dataset(labels, media_root, tmp_path / "canonical-out", frame_count=2)
    assert report["clip_count"] == 3


def test_prepare_rejects_shared_session_as_non_independent(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    rows = []
    for index in range(3):
        rows.append(
            {
                "schema_version": "caferoomba.record.v1",
                "status": "reviewed",
                "run_id": f"run-{index}",
                "session_id": "same-session",
                "decision_timestamp_ms": 2000,
                "video_path": f"run-{index}/video.mp4",
                "video_sha256": f"{index + 1:064x}",
                "viewpoint": "FPV",
                "action": "STOP",
                "turn180_onset": False,
                "label_source": "human",
                "reviewer": "reviewer",
                "is_synthetic": False,
            }
        )
    labels = media_root / "labels.jsonl"
    _write_labels(labels, rows)
    with pytest.raises(PrepareError, match="at least 3 independent run groups"):
        prepare_dataset(labels, media_root, tmp_path / "out")


def test_prepare_rejects_traversal_and_existing_output(tmp_path: Path) -> None:
    media_root = tmp_path / "workspace"
    media_root.mkdir()
    rows = _reviewed_rows(media_root)
    rows[0]["video_path"] = "../outside.mp4"
    labels = media_root / "labels.jsonl"
    _write_labels(labels, rows)
    with pytest.raises(PrepareError, match="escapes or is missing"):
        prepare_dataset(labels, media_root, tmp_path / "out")

    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(PrepareError, match="refusing to overwrite"):
        prepare_dataset(labels, media_root, existing)
    assert marker.read_text(encoding="utf-8") == "keep"
