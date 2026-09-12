"""Generated-video integration only: not owner demonstrations or accuracy evidence."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import torch
from PIL import Image

from caferoomba.data.ingest import sha256_file


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")
def test_batched_extraction_preserves_actual_frame_pixels(tmp_path):
    from caferoomba.data.prepare import _extract_frames

    video = tmp_path / "motion.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
        "testsrc2=s=32x24:r=10:d=4", "-c:v", "mpeg4", "-threads", "1", str(video),
    ], check=True, capture_output=True)
    decoded = subprocess.check_output([
        "ffmpeg", "-v", "error", "-nostdin", "-i", str(video), "-vsync", "0",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
    ])
    selected = {0, 2, 9, 17, 31}
    destination = tmp_path / "selected"
    _extract_frames(video, selected, destination)
    frame_bytes = 32 * 24 * 3
    for index in selected:
        with Image.open(destination / f"{index:09d}.png") as image:
            assert image.convert("RGB").tobytes() == decoded[
                index * frame_bytes:(index + 1) * frame_bytes]


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="ffmpeg/ffprobe required")
def test_all_notebook_stages_with_generated_video(tmp_path, monkeypatch):
    torch.set_num_threads(2)
    media = tmp_path / "media"
    media.mkdir()
    rows = []
    for index, color in enumerate(("red", "green", "blue")):
        video = media / f"run-{index}.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
            f"color=c={color}:s=64x64:r=4:d=3", "-c:v", "mpeg4", "-threads", "1",
            str(video),
        ], check=True, capture_output=True)
        rows.append({
            "schema_version": "caferoomba.record.v1", "run_id": f"run-{index}",
            "video_path": video.name, "video_sha256": sha256_file(video),
            "decision_timestamp_ms": 2000, "viewpoint": "FPV", "action": "STOP",
            "turn180_onset": False, "label_source": "human", "reviewer": "test-only",
            "status": "reviewed", "is_synthetic": False,
            "notes": "GENERATED SOFTWARE TEST INPUT; flags exercise real-data validators only",
        })
    (tmp_path / "labels.reviewed.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setenv("CAFEROOMBA_EPOCHS", "1")
    monkeypatch.setenv("CAFEROOMBA_BATCH_SIZE", "2")
    monkeypatch.setenv("CAFEROOMBA_TRAIN_DEVICE", "cpu")
    monkeypatch.delenv("CAFEROOMBA_RESUME", raising=False)
    dataset, run = tmp_path / "dataset-v1", tmp_path / "run-v1"
    scope = {"Path": Path, "os": os, "WORKSPACE": tmp_path,
             "DATASET": dataset, "RUN": run, "MANIFEST": dataset / "manifest.json"}
    for name in ("01_prepare_and_annotate", "02_train_and_evaluate", "03_export_and_replay"):
        notebook = json.loads((Path("notebooks") / f"{name}.ipynb").read_text())
        for cell in notebook["cells"]:
            if cell["cell_type"] != "code":
                continue
            if set(cell["metadata"].get("tags", [])) & {"bootstrap", "configuration"}:
                continue
            exec(compile("".join(cell["source"]), name, "exec"), scope)
    assert scope["metrics"]["n"] == 1
    assert scope["exported"]["agrees"]
    assert scope["exported"]["checkpoint_sha256"] == scope["report"]["checkpoint_sha256"]
    assert scope["prediction"]["requires_cloud"] is False
    # Relocation of the self-contained dataset/run must not require original source videos.
    moved = tmp_path / "moved"
    moved.mkdir()
    shutil.move(str(dataset), moved / "dataset-v1")
    shutil.move(str(run), moved / "run-v1")
    from caferoomba.learning.pipeline import evaluate_run
    assert evaluate_run(moved / "dataset-v1/manifest.json", moved / "run-v1") == scope["metrics"]
