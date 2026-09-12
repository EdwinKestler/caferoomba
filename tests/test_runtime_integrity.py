"""Hardware-free tests for freshness, camera modality, and explicit shadow mode."""
import numpy as np
import pytest
from caferoomba.app.config import CompanionConfig
from caferoomba.app.loop import CompanionLoop
from caferoomba.app.fsm import MissionState
from caferoomba.control.intents import intent_from_policy
from caferoomba.control.safety import supervise
from caferoomba.perception.buffer import CausalFrameBuffer
from caferoomba.perception.camera import FrameSet
from caferoomba.perception.fake import FakeCamera
from caferoomba.policy.onboard import load_policy
from caferoomba.schemas import ActionLabel


class Clock:
    now = 1000
    def __call__(self): return self.now


class TimedCamera(FakeCamera):
    def __init__(self, clock):
        super().__init__()
        self.clock = clock
    def read(self):
        sample = super().read()
        sample.t_ms = self.clock.now
        return sample


class DelayedPolicy:
    def __init__(self, clock, delay=0): self.clock, self.delay = clock, delay
    def predict(self, frames):
        self.clock.now += self.delay
        return {'action_label': ActionLabel.RIGHT, 'turn180_score': 0.0}


def test_processing_latency_is_checked_at_dispatch():
    clock, cfg = Clock(), CompanionConfig()
    cfg.camera.frame_count = 1
    loop = CompanionLoop(cfg, camera=TimedCamera(clock), policy=DelayedPolicy(clock, 500), clock=clock)
    try:
        loop.start()
        row = loop.cycle()
        assert row['observation_age_ms'] == 500
        assert 'stale_observation' in row['reasons']
        assert row['state'] == 'FAULT' and row['action'] == 'STOP'
    finally:
        loop.stop()


def test_real_camera_profile_stays_hold_but_infers():
    clock, cfg = Clock(), CompanionConfig()
    cfg.camera.backend, cfg.camera.frame_count = 'realsense', 1
    loop = CompanionLoop(cfg, camera=TimedCamera(clock), policy=DelayedPolicy(clock), clock=clock)
    try:
        loop.start()
        row = loop.cycle()
        assert loop.fsm.state is MissionState.HOLD
        assert row['proposed_action'] == 'RIGHT' and row['action'] == 'STOP'
        assert row['commands_sent'] == 0 and row['shadow_only']
    finally:
        loop.stop()


def test_future_ir_duplicate_and_viewpoint_checks():
    buffer = CausalFrameBuffer(frame_count=1, size=8)
    rgb = np.zeros((8, 8, 3), np.uint8)
    first = FrameSet(rgb, 200, 'camera-a', frame_id=1)
    buffer.push(first)
    assert buffer.observation_age_ms(100) is None
    with pytest.raises(ValueError, match='duplicate'):
        buffer.push(first)
    with pytest.raises(ValueError, match='viewpoint'):
        buffer.push(FrameSet(rgb, 201, 'camera-b', frame_id=2))
    with pytest.raises(ValueError, match='infrared'):
        buffer.push(FrameSet(rgb, 202, 'camera-a', frame_id=2, modality='infrared'))


def test_nonzero_stop_and_future_intent_rejected():
    intent = intent_from_policy(action=ActionLabel.STOP, now_ms=1000)
    intent.speed_mps = .2
    assert 'nonzero_stop' in supervise(intent, now_ms=1000, observation_age_ms=1).reasons
    assert 'invalid_intent_time' in supervise(intent, now_ms=900, observation_age_ms=1).reasons
    assert 'stale_observation' in supervise(intent, now_ms=1000, observation_age_ms=-1).reasons


def test_missing_explicit_model_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_policy(str(tmp_path / 'missing.onnx'))


def test_config_rejects_invalid_rate_and_unknown_backend():
    with pytest.raises(ValueError): CompanionConfig(loop={'hz': -1})
    with pytest.raises(ValueError): CompanionConfig(camera={'backend': 'typo'})
