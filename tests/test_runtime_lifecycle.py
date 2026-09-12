"""Guards around lifecycle and historical GPIO entrypoints."""
import importlib

import pytest

from caferoomba.app.config import CompanionConfig
from caferoomba.app.loop import CompanionLoop
from caferoomba.control.intents import intent_from_policy
from caferoomba.control.safety import supervise
from caferoomba.control.turn180 import Turn180Machine, TurnState
from caferoomba.perception.fake import FakeCamera
from caferoomba.recording.run import RunRecorder
from caferoomba.schemas import ActionLabel
from caferoomba.vehicle.dry_run import DryRunVehicle


@pytest.mark.parametrize("name", ["robot", "robot_drive", "servo", "drive",
                                  "cofee_rover", "continuous_drive"])
def test_legacy_entrypoints_fail_before_gpio_import(name):
    with pytest.raises(RuntimeError, match="Legacy GPIO"):
        importlib.import_module("rover." + name)


def test_unknown_clearance_blocks_movement_but_allows_stop():
    for action in [ActionLabel.STRAIGHT, ActionLabel.STOP]:
        result = supervise(intent_from_policy(action=action, now_ms=10),
                           now_ms=10, observation_age_ms=0,
                           heartbeat_ok=True, vehicle_health_ok=True)
        assert result.allow == (action is ActionLabel.STOP)


def test_abort_stops_active_turn():
    turn = Turn180Machine()
    turn.trigger(0, 1, footprint_clear=True)
    turn.abort()
    assert turn.step(1, .1, footprint_clear=True) is TurnState.STOP_FAULT


def test_start_failure_closes_vehicle():
    class BrokenCamera(FakeCamera):
        def open(self):
            raise RuntimeError("camera unplugged")

    vehicle = DryRunVehicle()
    runtime = CompanionLoop(CompanionConfig(), camera=BrokenCamera(), vehicle=vehicle)
    with pytest.raises(RuntimeError, match="unplugged"):
        runtime.start()
    assert not vehicle._connected
    assert not runtime._started


def test_recorder_rejects_records_outside_lifetime(tmp_path):
    recorder = RunRecorder(tmp_path)
    with pytest.raises(RuntimeError, match="open recorder"):
        recorder.record({})
    recorder.open()
    recorder.record({"test": True})
    recorder.close()
    with pytest.raises(RuntimeError, match="open recorder"):
        recorder.record({})


def test_camera_stall_faults_before_buffer_is_ready():
    now = [1000]

    class StallsEarly(FakeCamera):
        def read(self):
            if now[0] > 1000:
                return None
            frame = super().read()
            frame.t_ms = now[0]
            return frame

    runtime = CompanionLoop(CompanionConfig(camera={"backend": "usb"}),
                            camera=StallsEarly(), clock=lambda: now[0])
    try:
        runtime.start()
        runtime.cycle()
        now[0] = 2000
        row = runtime.cycle()
        assert not row["buffer_ready"]
        assert row["state"] == "FAULT"
        assert "stale_observation" in row["reasons"]
    finally:
        runtime.stop()
