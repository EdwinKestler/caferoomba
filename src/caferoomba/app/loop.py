"""Observe -> infer -> validate -> log. Every vehicle backend is non-actuating.

Real sensors stay in HOLD while shadow predictions are recorded. Only the
explicit fake-camera/dry-run demo auto-starts. Camera acquisition and recording
have dedicated workers. Freshness is re-evaluated AFTER inference at dispatch.
An independent actuator watchdog is still required before enabling real drive.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import asdict
from pathlib import Path

from caferoomba.app.bootstrap import apply_overrides as apply_overrides
from caferoomba.app.bootstrap import build_camera as build_camera
from caferoomba.app.bootstrap import build_vehicle as build_vehicle
from caferoomba.app.config import CompanionConfig
from caferoomba.app.fsm import MissionEvent, MissionFsm, MissionState
from caferoomba.control.intents import intent_from_policy
from caferoomba.control.turn180 import Turn180Machine, TurnState
from caferoomba.geofence.fence import Fence
from caferoomba.perception.buffer import CausalFrameBuffer
from caferoomba.policy.onboard import load_policy
from caferoomba.recording.run import RunRecorder
from caferoomba.schemas import ActionLabel


class CompanionLoop:
    """Composition-based runtime; dependencies/clock can be injected for offline tests."""
    def __init__(
        self, config: CompanionConfig, *, camera=None, vehicle=None, policy=None, clock=None
    ):
        self.config = CompanionConfig.model_validate(config.model_dump())
        if config.vehicle.allow_commands:
            raise RuntimeError("vehicle commands are not enabled")
        self.clock = clock or (lambda: int(time.monotonic() * 1000))
        self.fsm, self.turn = MissionFsm(), Turn180Machine()
        self.camera = camera or build_camera(config)
        self.vehicle = vehicle or build_vehicle(config)
        f = config.fence
        self.fence = Fence(required=f.required, kml_path=f.kml_path, region_name=f.region_name,
                           exclusion_names=f.exclusion_names, clearance_m=f.clearance_m,
                           member=f.kmz_member)
        self.policy = policy or load_policy(
            config.policy.onnx_path, execution_providers=config.policy.execution_providers
        )
        c = config.camera
        if c.width != c.height:
            raise ValueError("policy preprocessing currently requires a square target")
        self.buffer = CausalFrameBuffer(frame_count=c.frame_count, size=c.width,
                                       sample_period_ms=c.sample_period_ms,
                                       max_gap_ms=c.max_frame_gap_ms)
        record_dir = config.loop.record_dir
        self.recorder = (
            RunRecorder(Path(record_dir), save_frames=config.loop.record_frames)
            if record_dir
            else None
        )
        self.cycles = deque(maxlen=config.loop.history_limit)
        self.total_cycles = 0
        self._last_ms = self._sample = None
        self._started = False
        self._started_ms = None
        self.simulated_work_s = 0.0
        self.turn_clearance = False
        self.next_pass_aligned = False
        self.simulation = (c.backend == "fake" and config.vehicle.backend == "dry-run")

    def start(self):
        self.fsm.step(MissionEvent.BOOT)
        try:
            if self.recorder:
                self.recorder.open()
            self.fence.load()
            self.vehicle.connect()
            self.camera.open()
            self.fsm.step(MissionEvent.SENSORS_OK)
            self._started = True
            self._started_ms = self.clock()
        except Exception:
            self.fsm.step(MissionEvent.SENSORS_FAIL)
            self.stop()
            raise

    def _stop_intent(self, now):
        return intent_from_policy(action=ActionLabel.STOP, now_ms=now,
                                  ttl_ms=self.config.policy.ttl_ms, source="hold-zero")

    def _fault(self):
        self.turn.abort()
        if self.fsm.allowed(MissionEvent.FAULT):
            self.fsm.step(MissionEvent.FAULT)

    def cycle(self):
        if not self._started:
            raise RuntimeError("CompanionLoop.cycle requires start()")
        before = self.clock()
        if self.fsm.requires_zero_velocity() and self.turn.state not in {
            TurnState.SWEEP, TurnState.STOP_FAULT
        }:
            self.turn.abort()
        sample, prediction, errors = None, None, []
        try:
            sample = self.camera.read()
            if sample is not None:
                self._sample = sample
                self.buffer.push(sample)
            blocked = {MissionState.ESTOP, MissionState.FAULT}
            if self.buffer.ready() and self.fsm.state not in blocked:
                prediction = self.policy.predict(self.buffer.stack())
                action = ActionLabel(prediction["action_label"])
                score = float(prediction["turn180_score"])
                if not math.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError("invalid policy turn score")
            else:
                action, score = ActionLabel.STOP, 0.0
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            action, score = ActionLabel.STOP, 0.0
            self._fault()
        now = self.clock()  # Never reuse pre-inference time for freshness/expiry checks.
        try:
            telem = self.vehicle.telemetry()
        except Exception as exc:
            from caferoomba.vehicle.client import TelemetrySnapshot
            telem = TelemetrySnapshot(heartbeat_ok=False, link_error=str(exc))
            errors.append(f"telemetry failed: {type(exc).__name__}: {exc}")
            self._fault()
        if not telem.heartbeat_ok or not telem.vehicle_health_ok:
            self._fault()
        age = self.buffer.observation_age_ms(now)
        ready = self.buffer.ready()
        geofence_ok = self.fence.allows(telem.latitude_deg, telem.longitude_deg)
        if self.config.fence.required and not telem.gps_ok:
            geofence_ok = False
        dt = 0.0 if self._last_ms is None else max(0, now - self._last_ms) / 1000
        self._last_ms = now
        if (self.simulation and self.config.loop.auto_start_simulation and
            self.fsm.state is MissionState.HOLD and ready and telem.heartbeat_ok and
            geofence_ok and age is not None and age <= self.config.loop.max_observation_age_ms):
            self.fsm.step(MissionEvent.START_SWEEP)
        intent = self._stop_intent(now)
        if not self.fsm.requires_zero_velocity() and ready and not errors:
            intent = intent_from_policy(action=action, now_ms=before,
                                        ttl_ms=self.config.policy.ttl_ms,
                                        turn180_score=score, source="student-shadow")
            if self.fsm.state is MissionState.SWEEP and intent.turn180_trigger:
                if telem.heading_deg is None:
                    errors.append("turn trigger has no fresh heading")
                    self._fault()
                else:
                    self.turn.trigger(math.radians(-telem.heading_deg),
                                      -1 if action is ActionLabel.RIGHT else 1,
                                      footprint_clear=self.turn_clearance)
                    self.fsm.step(MissionEvent.TURN_TRIGGER)
            if self.fsm.state is MissionState.TURN:
                self._turn_step(telem, dt)
                intent = self._stop_intent(now)
                # TURN is supervised, but commands remain logged only.
                if self.turn.state is TurnState.TURNING:
                    intent.yaw_rate_rad_s = 0.3 * self.turn.direction
                    intent.action = (
                        ActionLabel.LEFT if self.turn.direction > 0 else ActionLabel.RIGHT
                    )
            if self.fsm.requires_zero_velocity():
                intent = self._stop_intent(now)
        decision = self.vehicle.send_intent(
            intent, now_ms=now, observation_age_ms=age,
            max_observation_age_ms=self.config.loop.max_observation_age_ms,
            heartbeat_ok=telem.heartbeat_ok, vehicle_health_ok=telem.vehicle_health_ok,
            geofence_ok=geofence_ok,
            footprint_clear=self.simulation or self.turn_clearance,
            required_sensor_missing=not ready and not self.fsm.requires_zero_velocity(),
            nan_prediction=bool(errors), operator_stop=self.fsm.state is MissionState.ESTOP)
        acquisition_expired = (
            self._sample is not None and
            (age is None or age > self.config.loop.max_observation_age_ms)
        ) or (
            self._sample is None and self._started_ms is not None and
            now - self._started_ms > self.config.loop.max_observation_age_ms
        )
        if not decision.allow and (ready or acquisition_expired):
            self._fault()
        if self.simulation and decision.allow and self.fsm.state is MissionState.SWEEP:
            self.simulated_work_s += dt
            if self.simulated_work_s >= self.config.loop.work_s:
                self.fsm.step(MissionEvent.WORK_DONE)
        row = {"state": self.fsm.state.value, "allow": decision.allow,
               "action": decision.action.value, "proposed_action": action.value,
               "turn180_score": score, "turn_state": self.turn.state.value,
               "reasons": decision.reasons, "errors": errors, "shadow_only": True,
               "commands_sent": 0, "dispatch_t_ms": now, "inference_cycle_ms": now - before,
               "observation_age_ms": age, "buffer_ready": ready,
               "telemetry": asdict(telem), "fence": self.fence.metadata(),
               "model_sha256": getattr(self.policy, "model_sha256", None),
               "execution_providers": getattr(self.policy, "execution_providers", []),
               "camera_frame_id": self._sample.frame_id if self._sample else None,
               "camera_t_ms": self._sample.t_ms if self._sample else None,
               "camera_modality": self._sample.modality if self._sample else None,
               "timestamp_quality": self._sample.timestamp_quality if self._sample else None,
               "camera_is_synthetic": self._sample.is_synthetic if self._sample else None}
        self.cycles.append(row)
        self.total_cycles += 1
        if self.recorder:
            self.recorder.record(row, sample)
        return row

    def _turn_step(self, telemetry, dt):
        if telemetry.heading_deg is None:
            self._fault()
            return
        state = self.turn.step(math.radians(-telemetry.heading_deg), dt,
                               footprint_clear=self.turn_clearance,
                               alignment_complete=self.next_pass_aligned)
        if state is TurnState.STOP_FAULT:
            self._fault()
        elif state is TurnState.SWEEP:
            self.next_pass_aligned = False
            self.fsm.step(MissionEvent.TURN_DONE)

    def stop(self):
        self._started = False
        self.turn.abort()
        errors = []
        for resource in (self.camera, self.vehicle):
            try:
                resource.close()
            except Exception as exc:
                errors.append(str(exc))
        if self.recorder and self.recorder.path.exists():
            self.recorder.close(summary={"state": self.fsm.state.value,
                                         "cycles": self.total_cycles, "cleanup_errors": errors,
                                         "shadow_only": True, "simulation": self.simulation})
        if errors:
            raise RuntimeError("cleanup failed: " + "; ".join(errors))

    def run(self, *, cycles):
        if cycles < 1:
            raise ValueError("cycles must be positive")
        try:
            self.start()
            for _ in range(cycles):
                started = time.monotonic()
                self.cycle()
                time.sleep(max(0, 1 / self.config.loop.hz - (time.monotonic() - started)))
        finally:
            self.stop()
        return list(self.cycles)


def run_from_path(config_path: Path | None, *, cycles: int):
    from caferoomba.app.config import load_config
    return CompanionLoop(load_config(config_path)).run(cycles=cycles)
