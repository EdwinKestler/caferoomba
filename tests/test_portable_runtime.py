"""Portable runtime guards; no cameras, serial ports, or training required."""
import pytest

from caferoomba.app.config import CompanionConfig
from caferoomba.app.loop import CompanionLoop
from caferoomba.vehicle.client import TelemetrySnapshot
from caferoomba.vehicle.dry_run import DryRunVehicle


class CriticalVehicle(DryRunVehicle):
    def telemetry(self):
        return TelemetrySnapshot(heartbeat_ok=True, vehicle_health_ok=False, system_status=5)


def test_critical_cube_faults_even_during_camera_warmup():
    runtime = CompanionLoop(CompanionConfig(), vehicle=CriticalVehicle())
    rows = runtime.run(cycles=1)
    assert rows[0]["state"] == "FAULT"
    assert rows[0]["action"] == "STOP"
    assert "vehicle_unhealthy" in rows[0]["reasons"]
    assert rows[0]["commands_sent"] == 0


def test_history_is_bounded_and_counts_all_cycles():
    cfg = CompanionConfig(loop={"history_limit": 2, "hz": 100})
    runtime = CompanionLoop(cfg)
    rows = runtime.run(cycles=5)
    assert len(rows) == 2
    assert runtime.total_cycles == 5
    assert rows[-1]["telemetry"]["is_synthetic"]


def test_cycle_requires_started_resources():
    with pytest.raises(RuntimeError, match="start"):
        CompanionLoop(CompanionConfig()).cycle()


def test_usb_configuration_does_not_open_devices():
    from caferoomba.app.bootstrap import build_camera
    cfg = CompanionConfig(camera={"backend": "usb", "device": "/dev/video999"})
    camera = build_camera(cfg)
    assert not camera.is_open()


def test_vehicle_exception_becomes_recorded_fault():
    class BrokenVehicle(DryRunVehicle):
        def telemetry(self):
            raise OSError("disconnected")

    runtime = CompanionLoop(CompanionConfig(), vehicle=BrokenVehicle())
    row = runtime.run(cycles=1)[0]
    assert row["state"] == "FAULT"
    assert "disconnected" in row["errors"][0]


def test_cli_does_not_report_success_for_fault(monkeypatch):
    from typer.testing import CliRunner

    import caferoomba.app.loop as loop_module
    from caferoomba.cli import app

    monkeypatch.setattr(loop_module, "build_vehicle", lambda cfg: CriticalVehicle())
    result = CliRunner().invoke(app, ["run-companion", "--cycles", "1"])
    assert result.exit_code == 1
    assert '"ok": false' in result.stdout
    assert '"armed": false' not in result.stdout
