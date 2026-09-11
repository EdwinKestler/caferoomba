import pytest
from pydantic import ValidationError

from caferoomba.data.clips import causal_window, clip_from_record, write_synthetic_frames
from caferoomba.data.ingest import IngestError, load_records, require_fpv_for_policy
from caferoomba.data.splits import assign_run_splits, detect_split_leakage
from caferoomba.data.synchronize import SyncError, check_sync
from caferoomba.schemas import (
    ActionLabel,
    DemonstrationRecord,
    LabelSource,
    Viewpoint,
)


def _record(**overrides):
    payload = dict(
        run_id="run-a",
        viewpoint=Viewpoint.FPV,
        decision_timestamp_ms=1000,
        action=ActionLabel.STRAIGHT,
        label_source=LabelSource.human,
        is_synthetic=True,
    )
    payload.update(overrides)
    return DemonstrationRecord(**payload)


def test_sync_rejects_large_offset():
    check_sync(video_timestamp_ms=1000, operator_timestamp_ms=1010, tolerance_ms=50)
    with pytest.raises(SyncError):
        check_sync(video_timestamp_ms=1000, operator_timestamp_ms=2000, tolerance_ms=50)


def test_causal_window_forbids_future_end():
    window = causal_window(1000, frame_count=4, period_ms=100)
    assert window.end_timestamp_ms == 1000
    assert window.start_timestamp_ms == 700
    assert window.includes_future_frames is False


def test_external_view_rejected_for_fpv_policy():
    records = [_record(viewpoint=Viewpoint.EXTERNAL)]
    with pytest.raises(IngestError):
        require_fpv_for_policy(records)


def test_missing_control_label_fails_validation(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        '[{"run_id":"x","viewpoint":"FPV","decision_timestamp_ms":1}]',
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_records(path)


def test_splits_keep_runs_together(tmp_path):
    clips = []
    for index in range(4):
        record = _record(run_id=f"run-{index}", decision_timestamp_ms=800)
        frames = write_synthetic_frames(tmp_path / record.run_id, action="STRAIGHT", frame_count=4)
        clips.append(clip_from_record(record, frames, frame_count=4, period_ms=200))
    mapping = assign_run_splits(clips)
    labeled = []
    from caferoomba.data.splits import apply_splits

    labeled = apply_splits(clips, mapping)
    assert detect_split_leakage(labeled) == []
    assert len(set(mapping.values())) == 3
