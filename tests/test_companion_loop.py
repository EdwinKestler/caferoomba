from caferoomba.app.config import CompanionConfig
from caferoomba.app.fsm import MissionState
from caferoomba.app.loop import CompanionLoop, build_vehicle
from caferoomba.perception.buffer import CausalFrameBuffer
from caferoomba.perception.fake import FakeCamera


def test_fake_camera_fills_causal_buffer():
    cam = FakeCamera(width=32, height=32)
    buf = CausalFrameBuffer(frame_count=4, size=32)
    cam.open()
    for _ in range(4):
        buf.push(cam.read())
    cam.close()
    stack = buf.stack()
    assert stack.shape == (1, 4, 3, 32, 32)
    assert buf.ready()


def test_dry_run_loop_reaches_sweep_without_arming():
    cfg = CompanionConfig()
    cfg.loop.hz = 100.0
    loop = CompanionLoop(cfg)
    rows = loop.run(cycles=12)
    assert loop.vehicle.telemetry().armed is False
    states = [row["state"] for row in rows]
    assert MissionState.HOLD.value in states
    assert MissionState.SWEEP.value in states
    assert MissionState.ESTOP.value not in states
    assert all(row["allow"] or row["state"] != MissionState.SWEEP.value for row in rows)


def test_cli_overrides_camera_vehicle():
    from caferoomba.app.config import CompanionConfig
    from caferoomba.app.loop import apply_overrides

    cfg = apply_overrides(CompanionConfig(), camera="realsense", vehicle="dry-run")
    assert cfg.camera.backend == "realsense"
    assert cfg.vehicle.backend == "dry-run"


def test_pr1_rejects_command_flag():
    cfg = CompanionConfig()
    cfg.vehicle.allow_commands = True
    try:
        build_vehicle(cfg)
        raise AssertionError("commands must be rejected")
    except RuntimeError as exc:
        assert "PR1" in str(exc) or "not enabled" in str(exc)
