"""Thread-safe telemetry snapshot, with separate freshness for each stream.

MAVLink raw latitude/longitude are 1e-7 degrees; ATTITUDE yaw is radians
(clockwise from north). Host receipt timestamps are not sensor capture times.
Raw RC observations are retained, never fabricated into human action labels.
"""
from __future__ import annotations

import math
import threading
from typing import Any, TypeAlias

from caferoomba.vehicle.client import (
    MagneticObservation,
    RangefinderObservation,
    ServoOutputObservation,
    SystemSensorMasks,
    TelemetrySnapshot,
)

# MAV_STATE_STANDBY and MAV_STATE_ACTIVE are the only states treated as
# operationally healthy. A fresh CRITICAL heartbeat still proves link liveness.
_HEALTHY_SYSTEM_STATES = {3, 4}
_AUXILIARY_MESSAGES = {
    "DISTANCE_SENSOR",
    "RAW_IMU",
    "SCALED_IMU",
    "SYS_STATUS",
    "SERVO_OUTPUT_RAW",
}
TelemetryRow: TypeAlias = tuple[int, dict[str, Any]]


class TelemetryCache:
    def __init__(
        self, *, system_id=1, heartbeat_timeout_ms=3000, gps_timeout_ms=1500
    ) -> None:
        self.system_id = system_id
        self.heartbeat_timeout_ms, self.gps_timeout_ms = heartbeat_timeout_ms, gps_timeout_ms
        self._lock, self.ready = threading.Lock(), threading.Event()
        self._data: dict[str, TelemetryRow] = {}
        self._error: str | None = None
        self.message_count = 0

    @property
    def error(self) -> str | None:
        with self._lock:
            return self._error

    def set_error(self, message: str) -> None:
        """Publish a receiver error atomically and wake a pending connect()."""
        with self._lock:
            self._error = message
            self.ready.set()

    def reset(self) -> None:
        """Discard all link-scoped state before a new serial connection."""
        with self._lock:
            self._data.clear()
            self._error = None
            self.message_count = 0
            self.ready.clear()

    def ingest(self, kind: str, fields: dict[str, Any], *, system_id: int, component_id: int,
               received_at_ms: int) -> bool:
        if system_id != self.system_id or component_id != 1:
            return False
        with self._lock:
            self.message_count += 1
            if kind == "HEARTBEAT":
                # MAV_TYPE_GROUND_ROVER=10, MAV_AUTOPILOT_ARDUPILOTMEGA=3.
                if fields.get("type") != 10 or fields.get("autopilot") != 3:
                    self._error = "expected ArduPilot ground-rover heartbeat"
                    self._data.pop("heartbeat", None)
                    self.ready.set()
                    return False
                self._error = None
                self._data["heartbeat"] = (received_at_ms, dict(fields))
                self.ready.set()
            elif kind in {"GPS_RAW_INT", "GLOBAL_POSITION_INT", "ATTITUDE", "VFR_HUD",
                          "RC_CHANNELS", "MANUAL_CONTROL"} | _AUXILIARY_MESSAGES:
                self._data[kind] = (received_at_ms, dict(fields))
        return True

    @staticmethod
    def _fresh(row: TelemetryRow | None, now_ms: int, ttl: int) -> bool:
        return row is not None and 0 <= now_ms - row[0] <= ttl

    @staticmethod
    def _bounded_int(value, lower: int, upper: int) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value if lower <= value <= upper else None

    @classmethod
    def _age(cls, row: TelemetryRow | None, now_ms: int, ttl_ms: int) -> int | None:
        if row is None or not cls._fresh(row, now_ms, ttl_ms):
            return None
        return now_ms - row[0]

    def _rangefinder(
        self, row: TelemetryRow | None, now_ms: int
    ) -> RangefinderObservation | None:
        if row is None:
            return None
        age = self._age(row, now_ms, self.gps_timeout_ms)
        if age is None:
            return None
        fields = row[1]
        current_cm = self._bounded_int(fields.get("current_distance"), 0, 65535)
        minimum_cm = self._bounded_int(fields.get("min_distance"), 0, 65535)
        maximum_cm = self._bounded_int(fields.get("max_distance"), 0, 65535)
        sensor_id = self._bounded_int(fields.get("id"), 0, 255)
        orientation = self._bounded_int(fields.get("orientation"), 0, 255)
        if (
            current_cm is None
            or minimum_cm is None
            or maximum_cm is None
            or sensor_id is None
            or orientation is None
        ):
            return None
        limits_valid = minimum_cm < maximum_cm
        return RangefinderObservation(
            distance_m=current_cm / 100.0,
            min_distance_m=minimum_cm / 100.0,
            max_distance_m=maximum_cm / 100.0,
            valid=limits_valid and minimum_cm <= current_cm <= maximum_cm,
            sensor_id=sensor_id,
            orientation=orientation,
            received_at_ms=row[0],
            age_ms=age,
        )

    def _magnetic(
        self, data: dict[str, TelemetryRow], now_ms: int
    ) -> MagneticObservation | None:
        rows = [(kind, data[kind]) for kind in ("RAW_IMU", "SCALED_IMU") if kind in data]
        if not rows:
            return None
        kind, row = max(rows, key=lambda item: item[1][0])
        age = self._age(row, now_ms, self.gps_timeout_ms)
        if age is None:
            return None
        fields = row[1]
        x_raw = self._bounded_int(fields.get("xmag"), -32768, 32767)
        y_raw = self._bounded_int(fields.get("ymag"), -32768, 32767)
        z_raw = self._bounded_int(fields.get("zmag"), -32768, 32767)
        if x_raw is None or y_raw is None or z_raw is None:
            return None
        sensor_id = None
        if kind == "RAW_IMU" and "id" in fields:
            sensor_id = self._bounded_int(fields.get("id"), 0, 255)
        return MagneticObservation(
            x_raw=x_raw,
            y_raw=y_raw,
            z_raw=z_raw,
            units="raw_sensor_counts" if kind == "RAW_IMU" else "milligauss",
            source_message="RAW_IMU" if kind == "RAW_IMU" else "SCALED_IMU",
            sensor_id=sensor_id,
            received_at_ms=row[0],
            age_ms=age,
        )

    def _system_sensors(
        self, row: TelemetryRow | None, now_ms: int
    ) -> SystemSensorMasks | None:
        if row is None:
            return None
        age = self._age(row, now_ms, self.gps_timeout_ms)
        if age is None:
            return None
        fields = row[1]
        present_mask = self._bounded_int(
            fields.get("onboard_control_sensors_present"), 0, 0xFFFFFFFF
        )
        enabled_mask = self._bounded_int(
            fields.get("onboard_control_sensors_enabled"), 0, 0xFFFFFFFF
        )
        health_mask = self._bounded_int(
            fields.get("onboard_control_sensors_health"), 0, 0xFFFFFFFF
        )
        if present_mask is None or enabled_mask is None or health_mask is None:
            return None
        return SystemSensorMasks(
            present_mask=present_mask,
            enabled_mask=enabled_mask,
            health_mask=health_mask,
            received_at_ms=row[0],
            age_ms=age,
        )

    def _servo_outputs(
        self, row: TelemetryRow | None, now_ms: int
    ) -> ServoOutputObservation | None:
        if row is None:
            return None
        age = self._age(row, now_ms, self.gps_timeout_ms)
        if age is None:
            return None
        fields = row[1]
        port = self._bounded_int(fields.get("port"), 0, 255)
        if port is None:
            return None
        values = tuple(
            self._bounded_int(fields.get(f"servo{channel}_raw"), 0, 65535)
            for channel in range(1, 17)
        )
        if all(value is None for value in values):
            return None
        return ServoOutputObservation(
            reported_pwm_us=values,
            port=port,
            received_at_ms=row[0],
            age_ms=age,
        )

    def snapshot(self, now_ms: int) -> TelemetrySnapshot:
        with self._lock:
            data, error = dict(self._data), self._error
        hb = data.get("heartbeat")
        heartbeat_ok = self._fresh(hb, now_ms, self.heartbeat_timeout_ms) and error is None
        system_status = (
            self._bounded_int(hb[1].get("system_status"), 0, 255) if hb else None
        )
        state = TelemetrySnapshot(
            heartbeat_ok=heartbeat_ok,
            vehicle_health_ok=heartbeat_ok and system_status in _HEALTHY_SYSTEM_STATES,
            system_status=system_status,
            link_error=error,
        )
        if hb:
            state.heartbeat_t_ms = hb[0]
        if heartbeat_ok and hb is not None:
            state.armed = bool(hb[1].get("base_mode", 0) & 128)
            state.mode = f"ROVER_CUSTOM_{hb[1].get('custom_mode', 'unknown')}"
            state.vehicle_type, state.autopilot_type = hb[1]["type"], hb[1]["autopilot"]
        fix = data.get("GPS_RAW_INT")
        global_position = data.get("GLOBAL_POSITION_INT")
        pos = global_position if self._fresh(
            global_position, now_ms, self.gps_timeout_ms
        ) else fix
        gps_ok = self._fresh(fix, now_ms, self.gps_timeout_ms)
        pos_ok = self._fresh(pos, now_ms, self.gps_timeout_ms)
        if gps_ok and pos_ok and fix is not None and pos is not None:
            lat, lon = pos[1].get("lat"), pos[1].get("lon")
            if lat is not None and lon is not None:
                lat, lon = lat / 1e7, lon / 1e7
                state.gps_ok = (fix[1].get("fix_type", 0) >= 3 and
                                math.isfinite(lat) and math.isfinite(lon) and
                                -90 <= lat <= 90 and -180 <= lon <= 180)
                if state.gps_ok:
                    state.latitude_deg, state.longitude_deg = lat, lon
                    state.position_t_ms = pos[0]
        attitude = data.get("ATTITUDE")
        if self._fresh(attitude, now_ms, self.gps_timeout_ms) and attitude is not None:
            yaw = attitude[1].get("yaw")
            if yaw is not None and math.isfinite(yaw):
                state.heading_deg = math.degrees(yaw) % 360
                state.heading_t_ms = attitude[0]
        hud = data.get("VFR_HUD")
        if self._fresh(hud, now_ms, self.gps_timeout_ms) and hud is not None:
            speed = hud[1].get("groundspeed")
            if speed is not None and math.isfinite(speed) and speed >= 0:
                state.velocity_mps = speed
        controls = [data[k] for k in ("RC_CHANNELS", "MANUAL_CONTROL") if k in data]
        if controls:
            latest = max(controls, key=lambda row: row[0])
            if self._fresh(latest, now_ms, self.gps_timeout_ms):
                state.operator_t_ms, state.operator_observation = latest
        state.rangefinder = self._rangefinder(data.get("DISTANCE_SENSOR"), now_ms)
        state.magnetic = self._magnetic(data, now_ms)
        state.system_sensors = self._system_sensors(data.get("SYS_STATUS"), now_ms)
        state.servo_outputs = self._servo_outputs(data.get("SERVO_OUTPUT_RAW"), now_ms)
        return state
