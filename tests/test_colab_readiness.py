"""Local preflight tests are not execution evidence from a Colab runtime."""

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from caferoomba.learning import readiness

ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40


def test_storage_smoke_preserves_existing_artifacts(tmp_path):
    artifact = tmp_path / "checkpoint.pt"
    artifact.write_bytes(b"do not modify")
    report = readiness.check_storage(tmp_path)
    assert report["write_replace_readback"] and report["cross_process_lock"]
    assert report["directory_fsync"]
    assert report["restart_persistence_verified"] is False
    assert list(tmp_path.iterdir()) == [artifact]
    assert artifact.read_bytes() == b"do not modify"


def test_storage_failure_cleans_up(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=0))
    with pytest.raises(RuntimeError, match="exclusion"):
        readiness.check_storage(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_storage_rejects_missing_workspace(tmp_path):
    with pytest.raises(FileNotFoundError):
        readiness.check_storage(tmp_path / "not-mounted")
    assert list(tmp_path.iterdir()) == []


def test_storage_rejects_unsupported_directory_fsync(tmp_path, monkeypatch):
    original = os.fsync

    def fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("directory fsync unsupported")
        original(fd)

    monkeypatch.setattr(readiness.os, "fsync", fsync)
    with pytest.raises(OSError, match="directory fsync unsupported"):
        readiness.check_storage(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_lock_probe_uses_writable_handle(tmp_path, monkeypatch):
    original = readiness.subprocess.run

    def run(command, **kwargs):
        assert "'r+b'" in command[2]
        return original(command, **kwargs)

    monkeypatch.setattr(readiness.subprocess, "run", run)
    assert readiness.check_storage(tmp_path)["cross_process_lock"]


@pytest.fixture
def clean_checkout(monkeypatch):
    monkeypatch.setattr(readiness.subprocess, "check_output", lambda command, **kwargs:
                        REVISION if "rev-parse" in command else "")


def test_setup_report(tmp_path, clean_checkout):
    report = readiness.check_setup(ROOT, tmp_path, REVISION)
    assert report["source_revision"] == REVISION
    assert report["requested_device"] == "cpu"
    assert report["training_executed"] is False
    assert report["cloud_runtime_created"] is False
    assert "ffprobe" in report["versions"]


@pytest.mark.parametrize("revision,device,error", [
    ("main", "cpu", "40-character"),
    (REVISION, "auto", "cpu or cuda"),
    ("b" * 40, "cpu", "revision differs"),
])
def test_setup_rejects_invalid_selection(tmp_path, clean_checkout, revision, device, error):
    with pytest.raises(ValueError, match=error):
        readiness.check_setup(ROOT, tmp_path, revision, device)


def test_setup_rejects_dirty_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(readiness.subprocess, "check_output", lambda command, **kwargs:
                        REVISION if "rev-parse" in command else " M file")
    with pytest.raises(ValueError, match="clean checkout"):
        readiness.check_setup(ROOT, tmp_path, REVISION)


def test_setup_rejects_missing_binary(tmp_path, clean_checkout, monkeypatch):
    monkeypatch.setattr(readiness.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="Missing required executable"):
        readiness.check_setup(ROOT, tmp_path, REVISION)


def test_setup_rejects_unavailable_cuda(tmp_path, clean_checkout, monkeypatch):
    import torch

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="CUDA requested but unavailable"):
        readiness.check_setup(ROOT, tmp_path, REVISION, "cuda")
