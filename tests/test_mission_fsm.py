import pytest

from caferoomba.app.fsm import (
    IllegalTransition,
    MissionEvent,
    MissionFsm,
    MissionState,
)


def test_happy_path_off_to_sweep_and_idle():
    fsm = MissionFsm()
    assert fsm.state is MissionState.OFF
    assert fsm.step(MissionEvent.BOOT) is MissionState.PRECHECK
    assert fsm.step(MissionEvent.SENSORS_OK) is MissionState.HOLD
    assert fsm.step(MissionEvent.START_SWEEP) is MissionState.SWEEP
    assert fsm.step(MissionEvent.TURN_TRIGGER) is MissionState.TURN
    assert fsm.step(MissionEvent.TURN_DONE) is MissionState.SWEEP
    assert fsm.step(MissionEvent.WORK_DONE) is MissionState.RETURN
    assert fsm.step(MissionEvent.WORK_DONE) is MissionState.IDLE


def test_illegal_transition_raises():
    fsm = MissionFsm()
    with pytest.raises(IllegalTransition):
        fsm.step(MissionEvent.START_SWEEP)


def test_estop_from_sweep_and_reset():
    fsm = MissionFsm()
    fsm.step(MissionEvent.BOOT)
    fsm.step(MissionEvent.SENSORS_OK)
    fsm.step(MissionEvent.START_SWEEP)
    assert fsm.step(MissionEvent.OPERATOR_STOP) is MissionState.ESTOP
    assert fsm.requires_zero_velocity()
    assert fsm.step(MissionEvent.RESET) is MissionState.OFF


def test_hold_and_fault_are_zero_velocity():
    fsm = MissionFsm(MissionState.HOLD)
    assert fsm.requires_zero_velocity()
    fsm = MissionFsm(MissionState.FAULT)
    assert fsm.requires_zero_velocity()
    fsm = MissionFsm(MissionState.SWEEP)
    assert not fsm.requires_zero_velocity()
