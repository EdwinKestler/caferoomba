"""Load demonstration JSONL and optional ffmpeg media. Never invent labels."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from caferoomba.schemas import DemonstrationRecord, Viewpoint


class IngestError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(path: Path) -> list[DemonstrationRecord]:
    text = path.read_text(encoding="utf-8")
    rows = json.loads(text) if path.suffix == ".json" else [
        json.loads(line) for line in text.splitlines() if line.strip()
    ]
    if not isinstance(rows, list):
        raise IngestError(f"{path} must contain a JSON list or JSONL")
    records = [DemonstrationRecord.model_validate(row) for row in rows]
    if not records:
        raise IngestError(f"{path} contains no demonstration records")
    return records


def require_fpv_for_policy(records: list[DemonstrationRecord]) -> None:
    bad = [item.run_id for item in records if item.viewpoint == Viewpoint.EXTERNAL]
    if bad:
        raise IngestError(
            f"external-view runs cannot enter an FPV policy dataset: {sorted(set(bad))}"
        )


def probe_video(path: Path) -> dict[str, str]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise IngestError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    return json.loads(result.stdout)
