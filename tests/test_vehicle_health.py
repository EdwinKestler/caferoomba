"""Hardware-free tests for bounded, passive Cube telemetry health."""

import time
from types import SimpleNamespace

import pytest

from caferoomba.vehicle.client import TelemetrySnapshot
from caferoomba.vehicle.dry_run import DryRunVehicle
from caferoomba.vehicle.serial_passive import PassiveSerialVehicle
from caferoomba.vehicle.telemetry import TelemetryCache


def _heartbeat(*, status=4, base_mode=0):
    return {
        "type": 10,
        "autopilot": 3,
        "base_mode": base_mode,
        "custom_mode": 7,
        "system_status": status,
    }


def _ingest(cache, kind, fields, received_at_ms=1_000):
    assert cache.ingest(
        kind,
        fields,
        system_id=1,
        component_id=1,
        received_at_ms=received_at_ms,
    )


def test_critical_heartbeat_proves_link_but_not_vehicle_health():
    cache = TelemetryCache(heartbeat_timeout_ms=500, gps_timeout_ms=200)
    _ingest(cache, "HEARTBEAT", _heartbeat(status=5))

    state = cache.snapshot(1_100)

    assert state.heartbeat_ok is True
    assert state.vehicle_health_ok is False
    assert state.system_status == 5
    assert state.armed is False


def test_unknown_vehicle_health_never_infers_health_from_link_liveness():
    state = TelemetrySnapshot(heartbeat_ok=True)
    assert state.vehicle_health_ok is False
    assert state.armed is None


def test_missing_or_stale_health_is_fail_closed_and_armed_becomes_unknown():
    cache = TelemetryCache(heartbeat_timeout_ms=500)
    _ingest(cache, "HEARTBEAT", _heartbeat(status=4, base_mode=128))
    assert cache.snapshot(1_100).armed is True

    stale = cache.snapshot(1_501)
    assert stale.heartbeat_ok is False
    assert stale.vehicle_health_ok is False
    assert stale.armed is None
    assert stale.heartbeat_t_ms == 1_000
    assert stale.system_status == 4

    missing_status = TelemetryCache()
    _ingest(missing_status, "HEARTBEAT", _heartbeat(status=None))
    state = missing_status.snapshot(1_001)
    assert state.heartbeat_ok is True
    assert state.vehicle_health_ok is False
    assert state.system_status is None


def test_fresh_typed_cube_observations_are_bounded_and_aged():
    cache = TelemetryCache(gps_timeout_ms=200)
    _ingest(
        cache,
        "DISTANCE_SENSOR",
        {
            "current_distance": 250,
            "min_distance": 20,
            "max_distance": 500,
            "id": 2,
            "orientation": 25,
        },
    )
    _ingest(
        cache,
        "SCALED_IMU",
        {"xmag": 11, "ymag": -12, "zmag": 13},
        received_at_ms=1_010,
    )
    _ingest(
        cache,
        "SYS_STATUS",
        {
            "onboard_control_sensors_present": 0x11,
            "onboard_control_sensors_enabled": 0x10,
            "onboard_control_sensors_health": 0x10,
        },
        received_at_ms=1_020,
    )
    _ingest(
        cache,
        "SERVO_OUTPUT_RAW",
        {"port": 0, "servo1_raw": 1500, "servo8_raw": 1700},
        received_at_ms=1_030,
    )

    state = cache.snapshot(1_100)

    assert state.rangefinder is not None
    assert state.rangefinder.distance_m == 2.5
    assert state.rangefinder.min_distance_m == 0.2
    assert state.rangefinder.max_distance_m == 5.0
    assert state.rangefinder.valid is True
    assert (state.rangefinder.sensor_id, state.rangefinder.orientation) == (2, 25)
    assert state.rangefinder.age_ms == 100

    assert state.magnetic is not None
    assert (state.magnetic.x_raw, state.magnetic.y_raw, state.magnetic.z_raw) == (11, -12, 13)
    assert state.magnetic.units == "milligauss"
    assert state.magnetic.source_message == "SCALED_IMU"
    assert state.magnetic.age_ms == 90

    assert state.system_sensors is not None
    assert state.system_sensors.present_mask == 0x11
    assert state.system_sensors.enabled_mask == 0x10
    assert state.system_sensors.health_mask == 0x10
    assert state.system_sensors.age_ms == 80

    assert state.servo_outputs is not None
    assert len(state.servo_outputs.reported_pwm_us) == 16
    assert state.servo_outputs.reported_pwm_us[0] == 1500
    assert state.servo_outputs.reported_pwm_us[7] == 1700
    assert state.servo_outputs.reported_pwm_us[8] is None
    assert state.servo_outputs.age_ms == 70
    assert state.servo_outputs.movement_confirmed is False


@pytest.mark.parametrize(
    ("kind", "units", "sensor_id"),
    [("RAW_IMU", "raw_sensor_counts", 3), ("SCALED_IMU", "milligauss", None)],
)
def test_magnetic_units_distinguish_raw_and_scaled_messages(kind, units, sensor_id):
    cache = TelemetryCache(gps_timeout_ms=100)
    fields = {"xmag": -1, "ymag": 2, "zmag": -3}
    if sensor_id is not None:
        fields["id"] = sensor_id
    _ingest(cache, kind, fields)

    magnetic = cache.snapshot(1_001).magnetic

    assert magnetic is not None
    assert magnetic.units == units
    assert magnetic.sensor_id == sensor_id


def test_auxiliary_observations_expire_and_invalid_distance_is_not_clearance():
    cache = TelemetryCache(gps_timeout_ms=100)
    _ingest(
        cache,
        "DISTANCE_SENSOR",
        {
            "current_distance": 600,
            "min_distance": 20,
            "max_distance": 500,
            "id": 0,
            "orientation": 0,
        },
    )
    fresh = cache.snapshot(1_050)
    assert fresh.rangefinder is not None and fresh.rangefinder.valid is False
    assert cache.snapshot(1_101).rangefinder is None


def test_cache_reset_clears_ready_samples_count_and_error():
    cache = TelemetryCache()
    _ingest(cache, "HEARTBEAT", _heartbeat())
    cache.set_error("receiver failed")
    assert cache.ready.is_set()
    assert cache.message_count == 1

    cache.reset()

    assert not cache.ready.is_set()
    assert cache.error is None
    assert cache.message_count == 0
    state = cache.snapshot(1_001)
    assert state.heartbeat_ok is False
    assert state.vehicle_health_ok is False
    assert state.armed is None


def test_passive_reconnect_cannot_reuse_previous_heartbeat(monkeypatch, tmp_path):
    class Lease:
        def __init__(self, *_args):
            pass

        def acquire(self):
            pass

        def close(self):
            pass

    class Port:
        def read(self, _size):
            return b""

        def close(self):
            pass

    class Parser:
        robust_parsing = False

        def __init__(self, _sink):
            pass

        def parse_buffer(self, _data):
            return []

    config = SimpleNamespace(
        allow_commands=False,
        system_id=1,
        heartbeat_timeout_ms=500,
        gps_timeout_ms=200,
        connect_timeout_s=0.02,
        device="/dev/fake-cube",
        baud=115200,
    )
    monkeypatch.setattr(
        "caferoomba.vehicle.serial_passive.resolve_device", lambda _path: "/dev/fake"
    )
    monkeypatch.setattr("caferoomba.vehicle.serial_passive.SerialLease", Lease)
    vehicle = PassiveSerialVehicle(
        config,
        lock_dir=tmp_path,
        serial_factory=lambda *_a, **_k: Port(),
        parser_factory=Parser,
    )

    def first_receiver():
        _ingest(
            vehicle.cache,
            "HEARTBEAT",
            _heartbeat(),
            received_at_ms=int(time.monotonic() * 1000),
        )
        vehicle._stop.wait()

    vehicle._receive = first_receiver
    vehicle.connect()
    assert vehicle.telemetry().heartbeat_ok is True
    vehicle.close()

    vehicle._receive = lambda: None
    with pytest.raises(TimeoutError, match="no ArduPilot Rover heartbeat"):
        vehicle.connect()
    assert vehicle.cache.message_count == 0
    assert not vehicle.cache.ready.is_set()


def test_passive_close_retains_lease_when_receiver_is_stuck():
    class StuckThread:
        def join(self, timeout):
            assert timeout == 1

        def is_alive(self):
            return True

    class Port:
        closed = False

        def close(self):
            self.closed = True

    class Lease:
        closed = False

        def close(self):
            self.closed = True

    config = SimpleNamespace(
        allow_commands=False,
        system_id=1,
        heartbeat_timeout_ms=500,
        gps_timeout_ms=200,
    )
    vehicle = PassiveSerialVehicle(config)
    vehicle._thread = StuckThread()
    vehicle._port = Port()
    vehicle._lease = Lease()
    vehicle._connected = True

    with pytest.raises(RuntimeError, match="lease is retained"):
        vehicle.close()

    assert vehicle._port is None
    assert vehicle._lease is not None
    assert vehicle._lease.closed is False


def test_dry_run_reports_an_explicitly_healthy_synthetic_snapshot():
    state = DryRunVehicle().telemetry()
    assert state.heartbeat_ok is True
    assert state.vehicle_health_ok is True
    assert state.armed is False
    assert state.mode == "DRY_RUN"
    assert state.is_synthetic is True
