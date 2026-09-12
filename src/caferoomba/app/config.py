"""Validated runtime configuration. All vehicle backends remain non-actuating.

Native devices are opened explicitly by the runtime, never while parsing YAML.
Assignments are validated so CLI overrides cannot bypass numeric/type guards.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Frozen(BaseModel):
    # Historical name retained for import compatibility; configuration is mutable.
    model_config = ConfigDict(extra="forbid", validate_assignment=True, allow_inf_nan=False)


class CameraConfig(Frozen):
    backend: Literal["fake", "realsense", "usb", "imx219"] = "fake"
    device: str | None = None
    serial_number: str | None = None
    width: int = Field(default=64, ge=8, le=2048)
    height: int = Field(default=64, ge=8, le=2048)
    frame_count: int = Field(default=8, ge=1, le=64)
    capture_width: int = Field(default=640, ge=16, le=4096)
    capture_height: int = Field(default=480, ge=16, le=2160)
    fps: int = Field(default=15, ge=1, le=60)
    read_timeout_ms: int = Field(default=300, ge=20, le=1000)
    sensor_id: int = Field(default=0, ge=0, le=3)
    allow_infrared_diagnostics: bool = False
    sample_period_ms: int = Field(default=0, ge=0, le=1000)
    max_frame_gap_ms: int = Field(default=500, ge=1, le=5000)


class VehicleConfig(Frozen):
    backend: Literal["dry-run", "serial-passive", "mavsdk"] = "dry-run"
    device: str | None = None
    baud: int = Field(default=115200, ge=1200, le=3000000)
    allow_commands: bool = False
    heartbeat_timeout_ms: int = Field(default=3000, ge=100, le=10000)
    gps_timeout_ms: int = Field(default=1500, ge=100, le=10000)
    connect_timeout_s: float = Field(default=5.0, gt=0, le=30)
    system_id: int = Field(default=1, ge=1, le=254)


class FenceConfig(Frozen):
    required: bool = False
    kml_path: str | None = None
    region_name: str | None = None
    exclusion_names: tuple[str, ...] = ()
    kmz_member: str | None = None
    clearance_m: float = Field(default=0.0, ge=0, le=100)


class PolicyConfig(Frozen):
    onnx_path: str | None = None
    execution_providers: tuple[str, ...] = ("CPUExecutionProvider",)
    ttl_ms: int = Field(default=250, ge=10, le=1000)


class LoopConfig(Frozen):
    hz: float = Field(default=10.0, gt=0, le=100)
    max_observation_age_ms: int = Field(default=300, ge=1, le=5000)
    work_s: float = Field(default=1800.0, gt=0)
    record_dir: str | None = None
    record_frames: bool = False
    history_limit: int = Field(default=1000, ge=1, le=100000)
    # Only fake-camera + dry-run demos may auto-start; real hardware stays HOLD.
    auto_start_simulation: bool = True


class CompanionConfig(Frozen):
    camera: CameraConfig = Field(default_factory=CameraConfig)
    vehicle: VehicleConfig = Field(default_factory=VehicleConfig)
    fence: FenceConfig = Field(default_factory=FenceConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)


def load_config(path: Path | None) -> CompanionConfig:
    if path is None:
        return CompanionConfig()
    return CompanionConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
