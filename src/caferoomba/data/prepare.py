"""Prepare reviewed real FPV labels as portable, causal frame datasets.

Two JSONL input shapes are accepted:

* ``caferoomba.labels.v1`` rows produced by ``scripts/draft_fpv_jsonl.py``.
  These rows must explicitly set ``status`` to ``reviewed``.
* canonical ``caferoomba.record.v1`` :class:`DemonstrationRecord` rows extended
  with the same explicit ``status=reviewed`` workflow gate.

Relative ``video_path`` values are interpreted from ``media_root`` and must
remain within it.  Prepared manifests contain relative paths only.  Source
videos are hash-verified during preparation but are not copied; loading
re-verifies the self-contained manifest and extracted frames.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import ValidationError

from caferoomba.data.clips import assert_causal, clip_from_record
from caferoomba.data.ingest import sha256_file
from caferoomba.data.splits import apply_splits, assign_run_splits, detect_split_leakage
from caferoomba.data.synchronize import SyncError, check_sync
from caferoomba.schemas import (
    SCHEMA_VERSION,
    ClipRecord,
    DemonstrationRecord,
    LabelSource,
    Viewpoint,
)

PREPARED_SCHEMA_VERSION = "caferoomba.prepared-dataset.v1"
_DRAFT_SCHEMA_VERSION = "caferoomba.labels.v1"
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_DRAFT_ONLY_FIELDS = {"clip_path", "status", "window_end_ms", "window_start_ms"}


class PrepareError(ValueError):
    """Raised when reviewed source data cannot safely become a dataset."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _dataset_digest(manifest: dict[str, Any]) -> str:
    unsigned = dict(manifest)
    unsigned.pop("dataset_sha256", None)
    return hashlib.sha256(_canonical_json(unsigned)).hexdigest()


def _contained_path(root: Path, candidate: Path, *, must_exist: bool) -> Path:
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise PrepareError(f"path escapes or is missing from root {root}: {candidate}") from exc
    return resolved


def _safe_relative_path(root: Path, value: object, *, kind: str) -> Path:
    if not isinstance(value, str) or not value:
        raise PrepareError(f"{kind} must be a non-empty relative path")
    pure = PurePosixPath(value)
    if "\\" in value or pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise PrepareError(f"unsafe {kind}: {value!r}")
    candidate = root.joinpath(*pure.parts)
    resolved = _contained_path(root, candidate, must_exist=True)
    if candidate.is_symlink() or not resolved.is_file():
        raise PrepareError(f"{kind} must be a regular non-symlink file: {value!r}")
    return resolved


def _read_rows(labels_path: Path) -> list[dict[str, Any]]:
    try:
        lines = labels_path.read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise PrepareError(f"cannot read labels JSONL {labels_path}: {exc}") from exc
    if not rows:
        raise PrepareError(f"{labels_path} contains no label rows")
    if not all(isinstance(row, dict) for row in rows):
        raise PrepareError("every labels JSONL row must be an object")
    return rows


def _record_from_row(row: dict[str, Any], *, row_number: int) -> DemonstrationRecord:
    schema = row.get("schema_version")
    payload = dict(row)
    if schema == _DRAFT_SCHEMA_VERSION:
        if row.get("status") != "reviewed":
            raise PrepareError(f"row {row_number}: draft label status must be reviewed")
        if row.get("window_end_ms") != row.get("decision_timestamp_ms"):
            raise PrepareError(f"row {row_number}: window_end_ms must equal decision_timestamp_ms")
        start = row.get("window_start_ms")
        end = row.get("window_end_ms")
        if type(start) is not int or type(end) is not int or start < 0 or start > end:
            raise PrepareError(f"row {row_number}: invalid draft label window")
        for field in _DRAFT_ONLY_FIELDS:
            payload.pop(field, None)
        payload["schema_version"] = SCHEMA_VERSION
    elif schema == SCHEMA_VERSION:
        status = payload.pop("status", None)
        if status != "reviewed":
            raise PrepareError(f"row {row_number}: canonical status must be reviewed")
    else:
        raise PrepareError(
            f"row {row_number}: unsupported schema_version {schema!r}; expected "
            f"{_DRAFT_SCHEMA_VERSION!r} or {SCHEMA_VERSION!r}"
        )

    required_explicit = (
        "action",
        "turn180_onset",
        "video_path",
        "video_sha256",
        "viewpoint",
        "label_source",
        "reviewer",
        "is_synthetic",
    )
    missing = [field for field in required_explicit if field not in row]
    if missing:
        raise PrepareError(f"row {row_number}: fields must be explicit: {missing}")
    if type(row.get("turn180_onset")) is not bool:
        raise PrepareError(f"row {row_number}: turn180_onset must be an explicit boolean")

    try:
        record = DemonstrationRecord.model_validate(payload)
    except ValidationError as exc:
        raise PrepareError(f"row {row_number}: invalid demonstration record: {exc}") from exc
    if not record.run_id.strip():
        raise PrepareError(f"row {row_number}: run_id must not be blank")
    if record.viewpoint != Viewpoint.FPV:
        raise PrepareError(f"row {row_number}: only viewpoint=FPV may enter this dataset")
    if record.label_source != LabelSource.human:
        raise PrepareError(f"row {row_number}: label_source must be human")
    if not record.reviewer or not record.reviewer.strip():
        raise PrepareError(f"row {row_number}: a non-empty human reviewer is required")
    if row.get("is_synthetic") is not False or record.is_synthetic is not False:
        raise PrepareError(f"row {row_number}: real FPV records require is_synthetic=false")
    if record.time_base != "pts":
        raise PrepareError(f"row {row_number}: time_base must be pts")
    if record.video_path is None or record.video_sha256 is None:
        raise PrepareError(f"row {row_number}: video_path and video_sha256 are required")
    if _SHA256_RE.fullmatch(record.video_sha256) is None:
        raise PrepareError(f"row {row_number}: video_sha256 must be lowercase SHA-256")
    return record


def _independent_groups(records: list[DemonstrationRecord]) -> list[set[str]]:
    runs = sorted({record.run_id for record in records})
    parent = {run_id: run_id for run_id in runs}

    def find(run_id: str) -> str:
        while parent[run_id] != run_id:
            parent[run_id] = parent[parent[run_id]]
            run_id = parent[run_id]
        return run_id

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    owners: dict[tuple[str, str], str] = {}
    for record in records:
        identities = [("video_sha256", str(record.video_sha256))]
        if record.session_id:
            identities.append(("session_id", record.session_id))
        for identity in identities:
            previous = owners.setdefault(identity, record.run_id)
            union(previous, record.run_id)

    groups: dict[str, set[str]] = defaultdict(set)
    for run_id in runs:
        groups[find(run_id)].add(run_id)
    result = sorted(groups.values(), key=lambda group: sorted(group))
    if len(result) < 3:
        raise PrepareError(
            "need at least 3 independent run groups after joining shared source videos "
            f"and sessions, found {len(result)}"
        )
    return result


def _split_mapping(clips: list[ClipRecord], groups: list[set[str]], seed: str) -> dict[str, str]:
    by_run = {clip.run_id: clip for clip in clips}
    representatives: list[ClipRecord] = []
    group_ids: dict[str, str] = {}
    for group in groups:
        run_ids = sorted(group)
        group_id = "group-" + hashlib.sha256("\0".join(run_ids).encode()).hexdigest()
        representatives.append(by_run[run_ids[0]].model_copy(update={"run_id": group_id}))
        for run_id in run_ids:
            group_ids[run_id] = group_id
    group_splits = assign_run_splits(representatives, seed=seed)
    return {run_id: group_splits[group_id] for run_id, group_id in group_ids.items()}


def _probe_frame_pts(video_path: Path) -> list[tuple[Decimal, str, int]]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "frame=pts_time",
        "-show_frames",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise PrepareError("ffprobe is required for real FPV preparation") from exc
    if result.returncode != 0:
        raise PrepareError(f"ffprobe failed for {video_path}: {result.stderr.strip()}")
    try:
        frames = json.loads(result.stdout).get("frames", [])
    except (AttributeError, json.JSONDecodeError) as exc:
        raise PrepareError(f"ffprobe returned invalid frame metadata for {video_path}") from exc
    parsed: list[tuple[Decimal, str, int]] = []
    for index, frame in enumerate(frames):
        raw = frame.get("pts_time") if isinstance(frame, dict) else None
        if raw is None:
            raise PrepareError(
                f"video frame {index} has no actual presentation timestamp: {video_path}"
            )
        try:
            pts_ms = Decimal(str(raw)) * 1000
        except InvalidOperation as exc:
            raise PrepareError(f"invalid presentation timestamp {raw!r}: {video_path}") from exc
        if not pts_ms.is_finite() or pts_ms < 0:
            raise PrepareError(f"negative or non-finite presentation timestamp: {raw!r}")
        parsed.append((pts_ms, str(raw), index))
    if not parsed:
        raise PrepareError(f"video has no decodable timestamped frames: {video_path}")
    if any(left[0] >= right[0] for left, right in zip(parsed, parsed[1:], strict=False)):
        raise PrepareError(
            f"video presentation timestamps are not strictly increasing: {video_path}"
        )
    return parsed


def _extract_frames(video_path: Path, frame_indices: set[int], directory: Path) -> None:
    """Decode one source once and materialize all selected frame indices."""

    ordered = sorted(frame_indices)
    if not ordered:
        return
    directory.mkdir(parents=True, exist_ok=True)
    for frame_index in ordered:
        if (directory / f"{frame_index:09d}.png").exists():
            raise PrepareError(f"refusing to overwrite prepared frame {frame_index}")
    filter_script = directory / ".select-filter.txt"
    pattern = directory / ".selected-%09d.png"
    expression = "+".join(f"eq(n\\,{frame_index})" for frame_index in ordered)
    filter_script.write_text(f"select={expression}\n", encoding="utf-8")
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
        "-filter_script:v",
        str(filter_script),
        "-frames:v",
        str(len(ordered)),
        "-vsync",
        "0",
        "-n",
        str(pattern),
    ]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise PrepareError("ffmpeg is required for real FPV preparation") from exc
    selected = sorted(directory.glob(".selected-*.png"))
    filter_script.unlink(missing_ok=True)
    if result.returncode != 0 or len(selected) != len(ordered):
        raise PrepareError(
            f"ffmpeg failed to extract {len(ordered)} selected frames from {video_path}: "
            f"{result.stderr.strip()}; produced {len(selected)}"
        )
    for temporary, frame_index in zip(selected, ordered, strict=True):
        temporary.rename(directory / f"{frame_index:09d}.png")


def _portable_source_path(media_root: Path, video_path: Path) -> str:
    return video_path.relative_to(media_root).as_posix()


def _select_frames(
    pts: list[tuple[Decimal, str, int]],
    requested_ms: list[int],
    *,
    max_frame_age_ms: int,
) -> list[tuple[Decimal, str, int, int]]:
    values = [row[0] for row in pts]
    selected: list[tuple[Decimal, str, int, int]] = []
    for requested in requested_ms:
        position = bisect.bisect_right(values, Decimal(requested)) - 1
        if position < 0:
            raise PrepareError(f"no frame exists at or before requested PTS {requested}ms")
        actual_ms, raw_pts, frame_index = pts[position]
        age = Decimal(requested) - actual_ms
        if age < 0:
            raise PrepareError("internal causality error: selected a future frame")
        if age > max_frame_age_ms:
            raise PrepareError(
                f"frame at {raw_pts}s is {age}ms old for requested PTS {requested}ms; "
                f"maximum is {max_frame_age_ms}ms"
            )
        selected.append((actual_ms, raw_pts, frame_index, requested))
    return selected


def _number(decimal: Decimal) -> int | float:
    integral = decimal.to_integral_value()
    return int(integral) if decimal == integral else float(decimal)


def _validate_split_isolation(clips: list[ClipRecord]) -> None:
    leaked_runs = detect_split_leakage(clips)
    if leaked_runs:
        raise PrepareError(f"run split leakage: {sorted(leaked_runs)}")
    for attribute in ("video_sha256", "session_id"):
        owners: dict[str, set[str]] = defaultdict(set)
        for clip in clips:
            value = getattr(clip.source, attribute)
            if value and clip.split:
                owners[str(value)].add(clip.split)
        leaked = sorted(value for value, splits in owners.items() if len(splits) > 1)
        if leaked:
            raise PrepareError(f"{attribute} split leakage: {leaked}")


def prepare_dataset(
    labels_path: Path,
    media_root: Path,
    output_dir: Path,
    frame_count: int = 8,
    period_ms: int = 250,
    max_frame_age_ms: int = 100,
    seed: str = "caferoomba-splits-v1",
) -> dict[str, Any]:
    """Prepare reviewed real FPV labels without overwriting a published dataset."""

    labels_path = Path(labels_path)
    media_root = Path(media_root)
    output_dir = Path(output_dir)
    if frame_count < 1 or period_ms <= 0 or max_frame_age_ms < 0:
        raise PrepareError("frame_count >= 1, period_ms > 0, and max_frame_age_ms >= 0 required")
    if not isinstance(seed, str) or not seed:
        raise PrepareError("seed must be a non-empty string")

    try:
        resolved_root = media_root.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise PrepareError(f"media_root does not exist: {media_root}") from exc
    try:
        resolved_labels = labels_path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as exc:
        raise PrepareError(f"labels_path does not exist: {labels_path}") from exc
    if labels_path.is_symlink() or not resolved_labels.is_file():
        raise PrepareError("labels_path must be a regular non-symlink file")
    if output_dir.exists() or output_dir.is_symlink():
        raise PrepareError(f"refusing to overwrite existing output path: {output_dir}")

    rows = _read_rows(resolved_labels)
    labels_sha256 = sha256_file(resolved_labels)
    records = [
        _record_from_row(row, row_number=index)
        for index, row in enumerate(rows, start=1)
    ]
    groups = _independent_groups(records)
    clip_ids = [f"{record.run_id}:{record.decision_timestamp_ms}" for record in records]
    if len(clip_ids) != len(set(clip_ids)):
        raise PrepareError("duplicate run_id and decision_timestamp_ms label")

    source_paths: dict[str, Path] = {}
    source_hashes_by_path: dict[Path, str] = {}
    normalized_records: list[DemonstrationRecord] = []
    for record in records:
        raw_video = Path(str(record.video_path))
        if "\\" in str(record.video_path) or raw_video.is_absolute():
            raise PrepareError(f"video_path must be relative: {record.video_path!r}")
        video = _contained_path(
            resolved_root, resolved_root / raw_video, must_exist=True
        )
        if video.is_symlink() or not video.is_file():
            raise PrepareError(
                f"video_path must be a regular non-symlink file: {record.video_path!r}"
            )
        if video not in source_hashes_by_path:
            source_hashes_by_path[video] = sha256_file(video)
        actual_hash = source_hashes_by_path[video]
        if actual_hash != record.video_sha256:
            raise PrepareError(
                f"source hash mismatch for {record.video_path}: expected "
                f"{record.video_sha256}, got {actual_hash}"
            )
        source_paths.setdefault(actual_hash, video)
        normalized_records.append(
            record.model_copy(
                update={"video_path": _portable_source_path(resolved_root, video)}
            )
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_dir.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise PrepareError(f"refusing to overwrite existing output path: {output_dir}") from exc

    try:
        pts_by_hash: dict[str, list[tuple[Decimal, str, int]]] = {}
        extracted: dict[tuple[str, int], tuple[str, str]] = {}
        clips: list[ClipRecord] = []
        frame_rows_by_clip: dict[str, list[dict[str, Any]]] = {}
        selections_by_clip: dict[str, list[tuple[Decimal, str, int, int]]] = {}
        required_by_hash: dict[str, set[int]] = defaultdict(set)

        for record in normalized_records:
            source_hash = str(record.video_sha256)
            video = source_paths[source_hash]
            if source_hash not in pts_by_hash:
                pts_by_hash[source_hash] = _probe_frame_pts(video)
            pts = pts_by_hash[source_hash]
            check_sync(
                video_timestamp_ms=record.decision_timestamp_ms,
                operator_timestamp_ms=record.operator_timestamp_ms,
                tolerance_ms=max_frame_age_ms,
            )
            start_ms = record.decision_timestamp_ms - (frame_count - 1) * period_ms
            if start_ms < 0:
                raise PrepareError(
                    f"causal window for {record.run_id}:{record.decision_timestamp_ms} "
                    "starts before video PTS zero"
                )
            requested_ms = [start_ms + index * period_ms for index in range(frame_count)]
            selected = _select_frames(
                pts, requested_ms, max_frame_age_ms=max_frame_age_ms
            )
            frame_paths = [
                f"frames/{source_hash}/{frame_index:09d}.png"
                for _, _, frame_index, _ in selected
            ]
            clip = clip_from_record(
                record, frame_paths, frame_count=frame_count, period_ms=period_ms
            )
            clips.append(clip)
            selections_by_clip[clip.clip_id] = selected
            required_by_hash[source_hash].update(row[2] for row in selected)

        for source_hash, frame_indices in required_by_hash.items():
            directory = output_dir / "frames" / source_hash
            _extract_frames(source_paths[source_hash], frame_indices, directory)
            for frame_index in frame_indices:
                relative = f"frames/{source_hash}/{frame_index:09d}.png"
                extracted[(source_hash, frame_index)] = (
                    relative,
                    sha256_file(output_dir / relative),
                )

        for clip in clips:
            source_hash = str(clip.source.video_sha256)
            frame_rows = []
            for actual_ms, raw_pts, frame_index, requested in selections_by_clip[clip.clip_id]:
                persisted_path, frame_hash = extracted[(source_hash, frame_index)]
                frame_rows.append(
                    {
                        "path": persisted_path,
                        "sha256": frame_hash,
                        "requested_timestamp_ms": requested,
                        "actual_pts_ms": _number(actual_ms),
                        "actual_pts_time": raw_pts,
                        "frame_index": frame_index,
                        "age_ms": _number(Decimal(requested) - actual_ms),
                    }
                )
            frame_rows_by_clip[clip.clip_id] = frame_rows

        mapping = _split_mapping(clips, groups, seed)
        clips = apply_splits(clips, mapping)
        _validate_split_isolation(clips)

        split_manifest: dict[str, dict[str, list[str]]] = {}
        for split in ("train", "val", "test"):
            members = [clip for clip in clips if clip.split == split]
            split_manifest[split] = {
                "clip_ids": sorted(clip.clip_id for clip in members),
                "run_ids": sorted({clip.run_id for clip in members}),
                "session_ids": sorted(
                    {clip.source.session_id for clip in members if clip.source.session_id}
                ),
                "video_sha256": sorted(
                    {str(clip.source.video_sha256) for clip in members}
                ),
            }

        for path, expected_hash in source_hashes_by_path.items():
            final_hash = sha256_file(path)
            if final_hash != expected_hash:
                raise PrepareError(
                    f"source changed during preparation: {path}; expected "
                    f"{expected_hash}, got {final_hash}"
                )
        final_labels_hash = sha256_file(resolved_labels)
        if final_labels_hash != labels_sha256:
            raise PrepareError(
                "labels file changed during preparation: expected "
                f"{labels_sha256}, got {final_labels_hash}"
            )
        sources = [
            {
                "path": _portable_source_path(resolved_root, path),
                "sha256": source_hash,
                "verified_during_preparation": True,
            }
            for path, source_hash in sorted(
                source_hashes_by_path.items(), key=lambda item: item[0].as_posix()
            )
        ]
        manifest: dict[str, Any] = {
            "schema_version": PREPARED_SCHEMA_VERSION,
            "config": {
                "frame_count": frame_count,
                "period_ms": period_ms,
                "max_frame_age_ms": max_frame_age_ms,
                "seed": seed,
            },
            "source_labels": {
                "name": resolved_labels.name,
                "sha256": labels_sha256,
                "verified_during_preparation": True,
            },
            "sources": sources,
            "split_manifest": split_manifest,
            "clips": [
                {
                    "record": clip.model_dump(mode="json"),
                    "frames": frame_rows_by_clip[clip.clip_id],
                }
                for clip in sorted(clips, key=lambda item: item.clip_id)
            ],
        }
        manifest["dataset_sha256"] = _dataset_digest(manifest)
        manifest_path = output_dir / "manifest.json"
        temporary_manifest = output_dir / ".manifest.json.tmp"
        temporary_manifest.write_bytes(_canonical_json(manifest) + b"\n")
        os.replace(temporary_manifest, manifest_path)
    except (PrepareError, SyncError, OSError, subprocess.SubprocessError):
        shutil.rmtree(output_dir, ignore_errors=True)
        raise

    split_counts = {
        split: len(details["clip_ids"]) for split, details in split_manifest.items()
    }
    return {
        "manifest": str(manifest_path.resolve()),
        "dataset_sha256": manifest["dataset_sha256"],
        "clip_count": len(clips),
        "split_counts": split_counts,
        "config": dict(manifest["config"]),
    }


def _validate_manifest_split_manifest(
    clips: list[ClipRecord], value: object
) -> None:
    if not isinstance(value, dict) or set(value) != {"train", "val", "test"}:
        raise PrepareError("manifest split_manifest must contain train, val, and test")
    expected: dict[str, dict[str, list[str]]] = {}
    for split in ("train", "val", "test"):
        members = [clip for clip in clips if clip.split == split]
        expected[split] = {
            "clip_ids": sorted(clip.clip_id for clip in members),
            "run_ids": sorted({clip.run_id for clip in members}),
            "session_ids": sorted(
                {clip.source.session_id for clip in members if clip.source.session_id}
            ),
            "video_sha256": sorted({str(clip.source.video_sha256) for clip in members}),
        }
    if value != expected:
        raise PrepareError("manifest split_manifest does not match clip ownership")


def load_prepared_dataset(manifest_path: Path) -> list[ClipRecord]:
    """Load and integrity-check a portable prepared dataset.

    Original source videos are deliberately not required at load time.  Their
    recorded hashes are preparation evidence; the manifest digest and every
    extracted frame byte are re-verified here.
    """

    manifest_path = Path(manifest_path).resolve(strict=True)
    root = manifest_path.parent
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise PrepareError("manifest_path must be a regular non-symlink file")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrepareError(f"cannot read prepared manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PrepareError("prepared manifest must be a JSON object")
    if manifest.get("schema_version") != PREPARED_SCHEMA_VERSION:
        raise PrepareError("unsupported prepared dataset schema")
    expected_digest = manifest.get("dataset_sha256")
    if not isinstance(expected_digest, str) or _SHA256_RE.fullmatch(expected_digest) is None:
        raise PrepareError("manifest dataset_sha256 is invalid")
    actual_digest = _dataset_digest(manifest)
    if actual_digest != expected_digest:
        raise PrepareError(
            f"dataset manifest digest mismatch: expected {expected_digest}, got {actual_digest}"
        )

    source_labels = manifest.get("source_labels")
    if not isinstance(source_labels, dict):
        raise PrepareError("manifest source_labels evidence is missing")
    label_name = source_labels.get("name")
    label_hash = source_labels.get("sha256")
    if (
        not isinstance(label_name, str)
        or not label_name
        or PurePosixPath(label_name).name != label_name
        or not isinstance(label_hash, str)
        or _SHA256_RE.fullmatch(label_hash) is None
        or source_labels.get("verified_during_preparation") is not True
    ):
        raise PrepareError("manifest source_labels evidence is invalid")

    config = manifest.get("config")
    if not isinstance(config, dict):
        raise PrepareError("manifest config is missing")
    try:
        frame_count = int(config["frame_count"])
        period_ms = int(config["period_ms"])
        max_frame_age_ms = int(config["max_frame_age_ms"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PrepareError("manifest frame configuration is invalid") from exc
    if frame_count < 1 or period_ms <= 0 or max_frame_age_ms < 0:
        raise PrepareError("manifest frame configuration is out of range")

    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PrepareError("manifest source evidence is missing")
    source_pairs: set[tuple[str, str]] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise PrepareError("invalid manifest source evidence")
        source_hash = source.get("sha256")
        source_path = source.get("path")
        if not isinstance(source_hash, str) or _SHA256_RE.fullmatch(source_hash) is None:
            raise PrepareError("invalid source SHA-256 evidence")
        if not isinstance(source_path, str) or not source_path:
            raise PrepareError("invalid source path evidence")
        pure_source = PurePosixPath(source_path)
        if (
            "\\" in source_path
            or pure_source.is_absolute()
            or ".." in pure_source.parts
            or "." in pure_source.parts
        ):
            raise PrepareError(f"unsafe source evidence path: {source_path!r}")
        if source.get("verified_during_preparation") is not True:
            raise PrepareError("source is not marked hash-verified during preparation")
        source_pairs.add((source_path, source_hash))

    clip_entries = manifest.get("clips")
    if not isinstance(clip_entries, list) or not clip_entries:
        raise PrepareError("manifest contains no clips")
    clips: list[ClipRecord] = []
    clip_ids: set[str] = set()
    verified_frames: dict[str, str] = {}
    for entry in clip_entries:
        if not isinstance(entry, dict):
            raise PrepareError("invalid clip manifest entry")
        try:
            clip = ClipRecord.model_validate(entry["record"])
        except (KeyError, ValidationError) as exc:
            raise PrepareError(f"invalid prepared clip record: {exc}") from exc
        if clip.clip_id in clip_ids:
            raise PrepareError(f"duplicate prepared clip_id: {clip.clip_id}")
        clip_ids.add(clip.clip_id)
        assert_causal(clip.window)
        if clip.window.frame_count != frame_count:
            raise PrepareError(f"clip {clip.clip_id} frame_count differs from manifest config")
        if clip.source.is_synthetic or clip.source.viewpoint != Viewpoint.FPV:
            raise PrepareError(f"clip {clip.clip_id} is not real FPV data")
        if clip.source.label_source != LabelSource.human or not clip.source.reviewer:
            raise PrepareError(f"clip {clip.clip_id} lacks a human review label")
        source_identity = (str(clip.source.video_path), str(clip.source.video_sha256))
        if source_identity not in source_pairs:
            raise PrepareError(f"clip {clip.clip_id} source is absent from source evidence")
        frames = entry.get("frames")
        if not isinstance(frames, list) or len(frames) != frame_count:
            raise PrepareError(f"clip {clip.clip_id} has invalid frame metadata count")
        if len(clip.frame_paths) != frame_count:
            raise PrepareError(f"clip {clip.clip_id} has invalid frame path count")
        resolved_frame_paths: list[str] = []
        expected_requested = [
            clip.window.start_timestamp_ms + index * period_ms
            for index in range(frame_count)
        ]
        pairs = zip(frames, clip.frame_paths, strict=True)
        for index, (frame, persisted_path) in enumerate(pairs):
            if not isinstance(frame, dict) or frame.get("path") != persisted_path:
                raise PrepareError(f"clip {clip.clip_id} frame path metadata mismatch")
            path = _safe_relative_path(root, persisted_path, kind="prepared frame path")
            expected_hash = frame.get("sha256")
            if not isinstance(expected_hash, str) or _SHA256_RE.fullmatch(expected_hash) is None:
                raise PrepareError(f"clip {clip.clip_id} has invalid frame hash")
            previous_hash = verified_frames.get(persisted_path)
            if previous_hash is None:
                actual_hash = sha256_file(path)
                if actual_hash != expected_hash:
                    raise PrepareError(
                        f"prepared frame hash mismatch for {persisted_path}: expected "
                        f"{expected_hash}, got {actual_hash}"
                    )
                verified_frames[persisted_path] = expected_hash
            elif previous_hash != expected_hash:
                raise PrepareError(f"conflicting hashes for prepared frame {persisted_path}")
            requested = frame.get("requested_timestamp_ms")
            try:
                actual_ms = Decimal(str(frame["actual_pts_ms"]))
                raw_actual_ms = Decimal(str(frame["actual_pts_time"])) * 1000
                age_ms = Decimal(str(frame["age_ms"]))
            except (KeyError, InvalidOperation) as exc:
                raise PrepareError(f"clip {clip.clip_id} has invalid PTS metadata") from exc
            if type(requested) is not int or requested != expected_requested[index]:
                raise PrepareError(f"clip {clip.clip_id} requested PTS grid is invalid")
            if actual_ms != raw_actual_ms:
                raise PrepareError(f"clip {clip.clip_id} actual PTS representations disagree")
            if actual_ms > requested:
                raise PrepareError(f"clip {clip.clip_id} includes a future frame")
            if age_ms != Decimal(requested) - actual_ms or age_ms > max_frame_age_ms:
                raise PrepareError(f"clip {clip.clip_id} frame age evidence is invalid")
            resolved_frame_paths.append(str(path))
        clips.append(clip.model_copy(update={"frame_paths": resolved_frame_paths}))

    _validate_split_isolation(clips)
    if {clip.split for clip in clips} != {"train", "val", "test"}:
        raise PrepareError("prepared clips must populate train, val, and test")
    _validate_manifest_split_manifest(clips, manifest.get("split_manifest"))
    return clips
