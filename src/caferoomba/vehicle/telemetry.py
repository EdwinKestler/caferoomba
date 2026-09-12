"""Thread-safe telemetry snapshot, with separate freshness for each stream.

MAVLink raw latitude/longitude are 1e-7 degrees; ATTITUDE yaw is radians
(clockwise from north). Host receipt timestamps are not sensor capture times.
Raw RC observations are retained, never fabricated into human action labels.
"""
from __future__ import annotations
import math
import threading
from caferoomba.vehicle.client import TelemetrySnapshot


class TelemetryCache:
    def __init__(self, *, system_id=1, heartbeat_timeout_ms=3000, gps_timeout_ms=1500):
        self.system_id = system_id
        self.heartbeat_timeout_ms, self.gps_timeout_ms = heartbeat_timeout_ms, gps_timeout_ms
        self._lock, self.ready = threading.Lock(), threading.Event()
        self._data = {}
        self.error = None
        self.message_count = 0

    def ingest(self, kind: str, fields: dict, *, system_id: int, component_id: int,
               received_at_ms: int) -> bool:
        if system_id != self.system_id or component_id != 1:
            return False
        with self._lock:
            self.message_count += 1
            if kind == "HEARTBEAT":
                # MAV_TYPE_GROUND_ROVER=10, MAV_AUTOPILOT_ARDUPILOTMEGA=3.
                if fields.get("type") != 10 or fields.get("autopilot") != 3:
                    self.error = "expected ArduPilot ground-rover heartbeat"
                    self._data.pop("heartbeat", None)
                    return False
                self.error = None
                self._data["heartbeat"] = (received_at_ms, dict(fields))
                self.ready.set()
            elif kind in {"GPS_RAW_INT", "GLOBAL_POSITION_INT", "ATTITUDE", "VFR_HUD",
                          "RC_CHANNELS", "MANUAL_CONTROL"}:
                self._data[kind] = (received_at_ms, dict(fields))
        return True

    @staticmethod
    def _fresh(row, now_ms, ttl):
        return row is not None and 0 <= now_ms - row[0] <= ttl

    def snapshot(self, now_ms: int) -> TelemetrySnapshot:
        with self._lock:
            data, error = dict(self._data), self.error
        hb = data.get("heartbeat")
        healthy = self._fresh(hb, now_ms, self.heartbeat_timeout_ms) and error is None
        state = TelemetrySnapshot(heartbeat_ok=healthy, link_error=error)
        if hb:
            state.heartbeat_t_ms = hb[0]
            state.armed = bool(hb[1].get("base_mode", 0) & 128)
            state.mode = f"ROVER_CUSTOM_{hb[1].get('custom_mode', 'unknown')}"
            state.vehicle_type, state.autopilot_type = hb[1]["type"], hb[1]["autopilot"]
        fix = data.get("GPS_RAW_INT")
        pos = data.get("GLOBAL_POSITION_INT") or fix
        if self._fresh(fix, now_ms, self.gps_timeout_ms) and self._fresh(pos, now_ms, self.gps_timeout_ms):
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
        if self._fresh(attitude, now_ms, self.gps_timeout_ms):
            yaw = attitude[1].get("yaw")
            if yaw is not None and math.isfinite(yaw):
                state.heading_deg = math.degrees(yaw) % 360
                state.heading_t_ms = attitude[0]
        hud = data.get("VFR_HUD")
        if self._fresh(hud, now_ms, self.gps_timeout_ms):
            speed = hud[1].get("groundspeed")
            if speed is not None and math.isfinite(speed) and speed >= 0:
                state.velocity_mps = speed
        controls = [data[k] for k in ("RC_CHANNELS", "MANUAL_CONTROL") if k in data]
        if controls:
            latest = max(controls, key=lambda row: row[0])
            if self._fresh(latest, now_ms, self.gps_timeout_ms):
                state.operator_t_ms, state.operator_observation = latest
        return state
