"""Sense → buffer → policy → supervise → dry-run act. No Cube commands."""

from __future__ import annotations

import time
from pathlib import Path

from caferoomba.app.config import CompanionConfig
from caferoomba.app.fsm import MissionEvent, MissionFsm, MissionState
from caferoomba.control.intents import intent_from_policy
from caferoomba.geofence.fence import Fence
from caferoomba.perception.buffer import CausalFrameBuffer
from caferoomba.perception.csi_imx219 import Imx219Camera
from caferoomba.perception.fake import FakeCamera
from caferoomba.perception.realsense import RealSenseCamera
from caferoomba.policy.onboard import load_policy
from caferoomba.schemas import ActionLabel
from caferoomba.vehicle.dry_run import DryRunVehicle


def apply_overrides(
    config: CompanionConfig,
    *,
    camera: str | None = None,
    vehicle: str | None = None,
) -> CompanionConfig:
    if camera:
        config.camera.backend = camera
    if vehicle:
        config.vehicle.backend = vehicle
    return config


def build_camera(config: CompanionConfig):
    backend = config.camera.backend
    if backend == "fake":
        return FakeCamera(width=config.camera.width, height=config.camera.height)
    if backend == "realsense":
        # D4xx color stream; buffer still resizes to camera.width/height for the policy.
        return RealSenseCamera(width=640, height=480)
    if backend == "imx219":
        return Imx219Camera()
    raise ValueError(f"unknown camera backend {backend!r}")


def build_vehicle(config: CompanionConfig):
    if config.vehicle.backend != "dry-run":
        raise ValueError("PR1 only supports vehicle.backend: dry-run")
    if config.vehicle.allow_commands:
        raise RuntimeError("vehicle commands are not enabled in PR1")
    return DryRunVehicle()


class CompanionLoop:
    """One companion process. ``run()`` does not arm and does not open MAVLink."""

    def __init__(self, config: CompanionConfig) -> None:
        self.config = config
        self.fsm = MissionFsm()
        self.camera = build_camera(config)
        self.vehicle = build_vehicle(config)
        self.fence = Fence(required=config.fence.required)
        self.policy = load_policy(config.policy.onnx_path)
        self.buffer = CausalFrameBuffer(
            frame_count=config.camera.frame_count,
            size=min(config.camera.width, config.camera.height),
        )
        self.cycles: list[dict] = []

    def start(self) -> None:
        self.fsm.step(MissionEvent.BOOT)
        self.camera.open()
        self.vehicle.connect()
        self.fsm.step(MissionEvent.SENSORS_OK)

    def stop(self) -> None:
        self.camera.close()
        self.vehicle.close()

    def _zero_intent(self, now_ms: int):
        return intent_from_policy(
            action=ActionLabel.STOP,
            now_ms=now_ms,
            ttl_ms=self.config.policy.ttl_ms,
            source="fsm-zero",
        )

    def cycle(self) -> dict:
        now_ms = int(time.monotonic() * 1000)
        sample = self.camera.read()
        self.buffer.push(sample)
        telem = self.vehicle.telemetry()
        geofence_ok = self.fence.allows(telem.latitude_deg, telem.longitude_deg)
        age = self.buffer.observation_age_ms(now_ms)
        missing = not self.buffer.ready()

        if self.fsm.state is MissionState.HOLD and self.buffer.ready():
            if telem.heartbeat_ok and geofence_ok and age is not None:
                self.fsm.step(MissionEvent.START_SWEEP)

        if self.fsm.requires_zero_velocity() or missing:
            intent = self._zero_intent(now_ms)
        else:
            prediction = self.policy.predict(self.buffer.stack())
            intent = intent_from_policy(
                action=prediction["action_label"],
                now_ms=now_ms,
                ttl_ms=self.config.policy.ttl_ms,
                turn180_score=float(prediction["turn180_score"]),
                source=str(prediction.get("backend", "policy")),
            )
            if intent.turn180_trigger and self.fsm.allowed(MissionEvent.TURN_TRIGGER):
                self.fsm.step(MissionEvent.TURN_TRIGGER)

        sweeping = self.fsm.state in {MissionState.SWEEP, MissionState.TURN}
        decision = self.vehicle.send_intent(
            intent,
            now_ms=now_ms,
            observation_age_ms=0 if age is None else age,
            heartbeat_ok=telem.heartbeat_ok,
            required_sensor_missing=missing if sweeping else False,
            geofence_ok=geofence_ok,
            operator_stop=self.fsm.state is MissionState.ESTOP,
        )
        if not decision.allow and sweeping and self.fsm.allowed(MissionEvent.FAULT):
            self.fsm.step(MissionEvent.FAULT)

        row = {
            "state": self.fsm.state.value,
            "allow": decision.allow,
            "action": decision.action.value,
            "reasons": decision.reasons,
            "observation_age_ms": age,
            "buffer_ready": self.buffer.ready(),
        }
        self.cycles.append(row)
        return row

    def run(self, *, cycles: int) -> list[dict]:
        period = 1.0 / max(self.config.loop.hz, 0.1)
        self.start()
        try:
            for _ in range(cycles):
                self.cycle()
                time.sleep(period)
        finally:
            self.stop()
        return self.cycles


def run_from_path(config_path: Path | None, *, cycles: int) -> list[dict]:
    from caferoomba.app.config import load_config

    return CompanionLoop(load_config(config_path)).run(cycles=cycles)
