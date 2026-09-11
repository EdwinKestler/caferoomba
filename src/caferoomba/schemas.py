"""Versioned CafeRoomba records. Missing telemetry is omitted, never zero-filled."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "caferoomba.record.v1"
CLASS_ORDER = ("LEFT", "STRAIGHT", "RIGHT", "STOP")


class EvidenceState(str, Enum):
    user_reported = "user_reported"
    implemented = "implemented"
    tested_offline = "tested_offline"
    tested_cloud = "tested_cloud"
    tested_on_device = "tested_on_device"
    planned = "planned"
    blocked = "blocked"


class ActionLabel(str, Enum):
    LEFT = "LEFT"
    STRAIGHT = "STRAIGHT"
    RIGHT = "RIGHT"
    STOP = "STOP"


class Viewpoint(str, Enum):
    FPV = "FPV"
    EXTERNAL = "EXTERNAL"
    SYNTHETIC = "SYNTHETIC"


class LabelSource(str, Enum):
    human = "human"
    teacher_suggestion = "teacher_suggestion"
    mixed = "mixed"


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DemonstrationRecord(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    run_id: str
    patch_id: str | None = None
    session_id: str | None = None
    recorded_at: str | None = None
    viewpoint: Viewpoint
    video_path: str | None = None
    video_sha256: str | None = None
    time_base: str = "pts"
    fps_nominal: float | None = None
    operator_command: str | None = None
    operator_timestamp_ms: int | None = None
    decision_timestamp_ms: int
    heading_deg: float | None = None
    heading_timestamp_ms: int | None = None
    position_m: tuple[float, float] | None = None
    velocity_observed_mps: float | None = None
    velocity_commanded_mps: float | None = None
    coordinate_frame: str = "body"
    units: str = "si"
    action: ActionLabel
    turn180_onset: bool = False
    turn180_direction: str | None = None
    turn180_state: str | None = None
    label_source: LabelSource = LabelSource.human
    reviewer: str | None = None
    sync_quality: str | None = None
    is_synthetic: bool = False
    notes: str | None = None

    @field_validator("velocity_observed_mps", "velocity_commanded_mps")
    @classmethod
    def _not_invented(cls, value: float | None) -> float | None:
        return value


class ClipWindow(FrozenModel):
    start_timestamp_ms: int
    end_timestamp_ms: int
    decision_timestamp_ms: int
    frame_count: int
    includes_future_frames: bool = False


class ClipRecord(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    clip_id: str
    run_id: str
    source: DemonstrationRecord
    window: ClipWindow
    frame_paths: list[str] = Field(default_factory=list)
    split: str | None = None


class TeacherAnnotation(FrozenModel):
    schema_version: str = "caferoomba.teacher.v1"
    clip_id: str
    backend: str
    model_id: str | None = None
    is_mock: bool
    patch_visible: bool | None = None
    boundary_ahead: bool | None = None
    suggested_action: ActionLabel | None = None
    turn180_trigger_candidate: bool | None = None
    normalized_visual_waypoint: tuple[float, float] | None = None
    brief_visible_evidence: str | None = None
    uncertainty: float | None = Field(default=None, ge=0.0, le=1.0)
    abstained: bool = False
    prompt_sha256: str
    input_sha256: str
    reviewed_by_human: bool = False
    human_agrees: bool | None = None
    generated_at: str | None = None


class Intent(FrozenModel):
    action: ActionLabel
    yaw_rate_rad_s: float | None = None
    speed_mps: float | None = None
    issued_at_ms: int
    expires_at_ms: int
    source: str
    valid: bool = True
    reason: str | None = None
    turn180_trigger: bool = False
    coordinate_frame: str = "body"


class SafetyDecision(FrozenModel):
    allow: bool
    action: ActionLabel
    reasons: list[str] = Field(default_factory=list)
    fail_closed: bool = True


class RunManifest(FrozenModel):
    schema_version: str = "caferoomba.manifest.v1"
    kind: str
    is_synthetic: bool
    evidence_state: EvidenceState
    command: str
    commit: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)
