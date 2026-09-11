"""YAML companion configuration. Constructors do not open hardware."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CameraConfig(Frozen):
    """Which camera backend to open. ``fake`` never touches USB or CSI."""

    backend: str = "fake"  # fake | realsense | imx219
    width: int = 64
    height: int = 64
    frame_count: int = 8


class VehicleConfig(Frozen):
    """Vehicle backend. ``dry-run`` never opens a serial port or arms."""

    backend: str = "dry-run"  # dry-run | mavsdk
    device: str | None = "/dev/ttyACM0"
    baud: int = 19200
    allow_commands: bool = False


class FenceConfig(Frozen):
    """PR1: fence is optional. Missing KML fail-closed is PR2."""

    required: bool = False
    kml_path: str | None = None


class PolicyConfig(Frozen):
    """ONNX path is optional. Missing file uses a constant STOP policy."""

    onnx_path: str | None = None
    ttl_ms: int = 250


class LoopConfig(Frozen):
    hz: float = 10.0
    max_observation_age_ms: int = 300


class CompanionConfig(Frozen):
    camera: CameraConfig = Field(default_factory=CameraConfig)
    vehicle: VehicleConfig = Field(default_factory=VehicleConfig)
    fence: FenceConfig = Field(default_factory=FenceConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)


def load_config(path: Path | None) -> CompanionConfig:
    if path is None:
        return CompanionConfig()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return CompanionConfig.model_validate(raw)
