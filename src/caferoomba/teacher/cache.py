"""Cache teacher outputs on model+prompt+input hashes only."""

from __future__ import annotations

from pathlib import Path

from caferoomba.schemas import TeacherAnnotation


def cache_key(model_id: str, prompt_sha256: str, input_sha256: str) -> str:
    return f"{model_id}:{prompt_sha256}:{input_sha256}"


def load_cached(directory: Path, key: str) -> TeacherAnnotation | None:
    path = directory / f"{key.replace(':', '_')}.json"
    if not path.is_file():
        return None
    return TeacherAnnotation.model_validate_json(path.read_text(encoding="utf-8"))


def store_cached(directory: Path, key: str, annotation: TeacherAnnotation) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{key.replace(':', '_')}.json"
    path.write_text(annotation.model_dump_json(indent=2), encoding="utf-8")
    return path
