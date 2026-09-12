"""VehicleClient protocol and bounded, receive-only telemetry records.

All timestamps and ages are based on host monotonic receipt time. Reported
servo PWM is an observation only; it is not proof that an actuator moved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from caferoomba.schemas import Intent, SafetyDecision


@dataclass(frozen=True)
class RangefinderObservation:
    """Latest fresh MAVLink ``DISTANCE_SENSOR`` report."""

    distance_m: float
    min_distance_m: float
    max_distance_m: float
    valid: bool
    sensor_id: int
    orientation: int
    received_at_ms: int
    age_ms: int


@dataclass(frozen=True)
class MagneticObservation:
    """Latest fresh magnetic vector, kept in its explicitly reported units."""

    x_raw: int
    y_raw: int
    z_raw: int
    units: Literal["raw_sensor_counts", "milligauss"]
    source_message: Literal["RAW_IMU", "SCALED_IMU"]
    received_at_ms: int
    age_ms: int
    sensor_id: int | None = None


@dataclass(frozen=True)
class SystemSensorMasks:
    """Latest fresh MAVLink ``SYS_STATUS`` sensor bitmasks."""

    present_mask: int
    enabled_mask: int
    health_mask: int
    received_at_ms: int
    age_ms: int


@dataclass(frozen=True)
class ServoOutputObservation:
    """Latest fresh reported PWM values; never evidence of physical movement."""

    reported_pwm_us: tuple[int | None, ...]
    port: int
    received_at_ms: int
    age_ms: int
    movement_confirmed: bool = field(default=False, init=False)


@dataclass
class TelemetrySnapshot:
    heartbeat_ok: bool
    vehicle_health_ok: bool = False
    gps_ok: bool = False
    heading_deg: float | None = None
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    armed: bool | None = None
    mode: str | None = None
    heartbeat_t_ms: int | None = None
    system_status: int | None = None
    position_t_ms: int | None = None
    heading_t_ms: int | None = None
    velocity_mps: float | None = None
    operator_observation: dict | None = None
    operator_t_ms: int | None = None
    vehicle_type: int | None = None
    autopilot_type: int | None = None
    rangefinder: RangefinderObservation | None = None
    magnetic: MagneticObservation | None = None
    system_sensors: SystemSensorMasks | None = None
    servo_outputs: ServoOutputObservation | None = None
    is_synthetic: bool = False
    link_error: str | None = None


class VehicleClient(Protocol):
    def connect(self) -> None:
        """Open the link. Dry-run is a no-op."""

    def close(self) -> None: ...

    def telemetry(self) -> TelemetrySnapshot: ...

    def send_intent(self, intent: Intent, **safety_kwargs) -> SafetyDecision: ...

    def arm(self) -> None:
        """Must raise. Companion software never arms."""
