
from caferoomba.control.intents import intent_from_policy, to_mavlink_yaw_rate
from caferoomba.control.mission import MissionScheduler
from caferoomba.control.patch_store import PatchStore
from caferoomba.control.safety import supervise
from caferoomba.control.turn180 import Turn180Machine, TurnState, wrap_pi
from caferoomba.schemas import ActionLabel


def _intent(action=ActionLabel.STRAIGHT, now=1000, ttl=250):
    return intent_from_policy(action=action, now_ms=now, ttl_ms=ttl)


def test_stale_nan_stop_fail_closed():
    intent = _intent()
    stale = supervise(intent, now_ms=1000, observation_age_ms=5000)
    assert stale.allow is False and stale.action is ActionLabel.STOP
    expired = supervise(_intent(now=1000, ttl=10), now_ms=2000, observation_age_ms=1)
    assert "expired_intent" in expired.reasons
    nan = supervise(intent, now_ms=1000, observation_age_ms=1, nan_prediction=True)
    assert "nan_prediction" in nan.reasons
    stop = supervise(intent, now_ms=1000, observation_age_ms=1, operator_stop=True)
    assert stop.action is ActionLabel.STOP


def test_yaw_sign_conversion():
    left = intent_from_policy(action=ActionLabel.LEFT, now_ms=0)
    right = intent_from_policy(action=ActionLabel.RIGHT, now_ms=0)
    assert left.yaw_rate_rad_s and left.yaw_rate_rad_s > 0
    assert right.yaw_rate_rad_s and right.yaw_rate_rad_s < 0
    assert to_mavlink_yaw_rate(left.yaw_rate_rad_s) < 0
    assert to_mavlink_yaw_rate(right.yaw_rate_rad_s) > 0


def test_turn180_wraparound_and_retrigger():
    machine = Turn180Machine(timeout_s=20)
    heading = 3.0
    assert machine.trigger(heading, 1, footprint_clear=True) is TurnState.TURNING
    for _ in range(40):
        heading = wrap_pi(heading + 0.2)
        machine.step(heading, 0.1, footprint_clear=True)
        if machine.state is TurnState.ALIGN_ADVANCE_PASS:
            break
    assert machine.state in {TurnState.ALIGN_ADVANCE_PASS, TurnState.SWEEP}
    machine.step(heading, 0.1, footprint_clear=True)
    assert machine.state is TurnState.SWEEP
    assert machine.trigger(heading, 1, footprint_clear=True) is TurnState.SWEEP  # cooldown


def test_turn180_blocked_footprint_faults():
    machine = Turn180Machine()
    machine.trigger(0.0, -1, footprint_clear=False)
    assert machine.state is TurnState.VERIFY_TURN_CLEARANCE
    machine.step(0.0, 0.1, footprint_clear=True)
    assert machine.state is TurnState.TURNING
    machine.step(0.1, 0.1, footprint_clear=False)
    assert machine.state is TurnState.STOP_FAULT


def test_mission_no_overlap_and_patch_radius(tmp_path):
    scheduler = MissionScheduler()
    scheduler.start()
    try:
        scheduler.start()
        raise AssertionError("overlap allowed")
    except RuntimeError:
        pass
    store = PatchStore(tmp_path / "patches.json", radius_m=2.0)
    first = store.record("a", 0.0, 0.0, 1.0)
    again = store.record("b", 0.5, 0.5, 2.0)
    assert again.patch_id == first.patch_id
    other = store.record("c", 10.0, 10.0, 3.0)
    assert other.patch_id == "c"
