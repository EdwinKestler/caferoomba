import pytest

from caferoomba.data.fixtures import build_synthetic_clips
from caferoomba.teacher.cosmos import TeacherError, annotate


def test_mock_teacher_is_explicitly_mock(tmp_path):
    clips = build_synthetic_clips(tmp_path)
    annotation = annotate(clips[0], backend="mock")
    assert annotation.is_mock is True
    assert annotation.backend == "mock"
    assert "not Cosmos" in annotation.brief_visible_evidence


def test_live_teacher_blocks_without_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("COSMOS_TEACHER_URL", raising=False)
    clips = build_synthetic_clips(tmp_path)
    with pytest.raises(TeacherError, match="blocked"):
        annotate(clips[0], backend="live")
