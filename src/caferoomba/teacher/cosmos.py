"""Offline teacher. Mock never counts as NVIDIA Cosmos evidence."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from caferoomba.schemas import ActionLabel, ClipRecord, TeacherAnnotation
from caferoomba.teacher.prompts import prompt_sha256

REQUESTED_MODEL_ID = "nvidia/cosmos3-nano-reasoner"


class TeacherError(RuntimeError):
    pass


def _input_hash(clip: ClipRecord) -> str:
    payload = "|".join(clip.frame_paths + [clip.clip_id, clip.window.model_dump_json()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def annotate_mock(clip: ClipRecord) -> TeacherAnnotation:
    """Deterministic fixture teacher. is_mock is always true."""
    action = clip.source.action
    return TeacherAnnotation(
        clip_id=clip.clip_id,
        backend="mock",
        model_id="caferoomba-mock-teacher",
        is_mock=True,
        patch_visible=action != ActionLabel.STOP,
        boundary_ahead=action in {ActionLabel.LEFT, ActionLabel.RIGHT},
        suggested_action=action,
        turn180_trigger_candidate=clip.source.turn180_onset,
        brief_visible_evidence="synthetic fixture heuristic; not Cosmos inference",
        uncertainty=0.5,
        abstained=False,
        prompt_sha256=prompt_sha256(),
        input_sha256=_input_hash(clip),
        reviewed_by_human=False,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def annotate_live(clip: ClipRecord, *, model_id: str = REQUESTED_MODEL_ID) -> TeacherAnnotation:
    url = os.environ.get("COSMOS_TEACHER_URL", "").strip()
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not url or not key:
        raise TeacherError(
            "live Cosmos teacher blocked: COSMOS_TEACHER_URL and NVIDIA_API_KEY "
            "are unset. Use backend=mock for fixtures. This is not Cosmos evidence."
        )
    raise TeacherError(
        f"live Cosmos teacher is configured for {model_id} but network annotation "
        "is not authorized in this CPU milestone (spending allowance is zero)"
    )


def annotate(clip: ClipRecord, *, backend: str = "mock") -> TeacherAnnotation:
    if backend == "mock":
        return annotate_mock(clip)
    if backend == "live":
        return annotate_live(clip)
    raise TeacherError(f"unknown teacher backend {backend!r}")
