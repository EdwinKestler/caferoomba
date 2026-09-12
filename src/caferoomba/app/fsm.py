"""Table-driven mission FSM. Software never arms the vehicle.

TURN is a mission state that *hosts* the existing TURN_180 sub-machine; it
does not replace it. HOLD/FAULT/ESTOP/OFF/PRECHECK/IDLE command zero velocity.
"""

from __future__ import annotations

from enum import Enum


class MissionState(str, Enum):
    OFF = "OFF"
    PRECHECK = "PRECHECK"
    HOLD = "HOLD"
    SWEEP = "SWEEP"
    TURN = "TURN"
    RETURN = "RETURN"
    IDLE = "IDLE"
    FAULT = "FAULT"
    ESTOP = "ESTOP"


class MissionEvent(str, Enum):
    BOOT = "BOOT"
    SENSORS_OK = "SENSORS_OK"
    SENSORS_FAIL = "SENSORS_FAIL"
    START_SWEEP = "START_SWEEP"
    TURN_TRIGGER = "TURN_TRIGGER"
    TURN_DONE = "TURN_DONE"
    WORK_DONE = "WORK_DONE"
    IDLE_DONE = "IDLE_DONE"
    FAULT = "FAULT"
    OPERATOR_STOP = "OPERATOR_STOP"
    RESET = "RESET"
    HOLD_REQUEST = "HOLD_REQUEST"
    HOME_ARRIVED = "HOME_ARRIVED"


class IllegalTransition(ValueError):
    """Raised when (state, event) is not in the table."""


# Explicit table only. Missing keys are illegal, not implicit no-ops.
TRANSITIONS: dict[tuple[MissionState, MissionEvent], MissionState] = {
    (MissionState.OFF, MissionEvent.BOOT): MissionState.PRECHECK,
    (MissionState.PRECHECK, MissionEvent.SENSORS_OK): MissionState.HOLD,
    (MissionState.PRECHECK, MissionEvent.SENSORS_FAIL): MissionState.FAULT,
    (MissionState.PRECHECK, MissionEvent.OPERATOR_STOP): MissionState.ESTOP,
    (MissionState.HOLD, MissionEvent.START_SWEEP): MissionState.SWEEP,
    (MissionState.HOLD, MissionEvent.SENSORS_FAIL): MissionState.FAULT,
    (MissionState.HOLD, MissionEvent.FAULT): MissionState.FAULT,
    (MissionState.HOLD, MissionEvent.OPERATOR_STOP): MissionState.ESTOP,
    (MissionState.SWEEP, MissionEvent.TURN_TRIGGER): MissionState.TURN,
    (MissionState.SWEEP, MissionEvent.WORK_DONE): MissionState.RETURN,
    (MissionState.SWEEP, MissionEvent.FAULT): MissionState.FAULT,
    (MissionState.SWEEP, MissionEvent.SENSORS_FAIL): MissionState.FAULT,
    (MissionState.SWEEP, MissionEvent.OPERATOR_STOP): MissionState.ESTOP,
    (MissionState.TURN, MissionEvent.TURN_DONE): MissionState.SWEEP,
    (MissionState.TURN, MissionEvent.FAULT): MissionState.FAULT,
    (MissionState.TURN, MissionEvent.OPERATOR_STOP): MissionState.ESTOP,
    (MissionState.RETURN, MissionEvent.WORK_DONE): MissionState.IDLE,
    (MissionState.RETURN, MissionEvent.FAULT): MissionState.FAULT,
    (MissionState.RETURN, MissionEvent.OPERATOR_STOP): MissionState.ESTOP,
    (MissionState.IDLE, MissionEvent.IDLE_DONE): MissionState.HOLD,
    (MissionState.IDLE, MissionEvent.OPERATOR_STOP): MissionState.ESTOP,
    (MissionState.IDLE, MissionEvent.FAULT): MissionState.FAULT,
    (MissionState.FAULT, MissionEvent.RESET): MissionState.PRECHECK,
    (MissionState.FAULT, MissionEvent.OPERATOR_STOP): MissionState.ESTOP,
    (MissionState.ESTOP, MissionEvent.RESET): MissionState.OFF,
}

for _state in (MissionState.SWEEP, MissionState.TURN, MissionState.RETURN):
    TRANSITIONS[(_state, MissionEvent.HOLD_REQUEST)] = MissionState.HOLD
TRANSITIONS[(MissionState.RETURN, MissionEvent.HOME_ARRIVED)] = MissionState.IDLE

ZERO_VELOCITY_STATES = frozenset(
    {
        MissionState.OFF,
        MissionState.PRECHECK,
        MissionState.HOLD,
        MissionState.IDLE,
        MissionState.FAULT,
        MissionState.ESTOP,
        MissionState.RETURN,
    }
)


class MissionFsm:
    """Object-oriented wrapper around TRANSITIONS. No side effects."""

    def __init__(self, state: MissionState = MissionState.OFF) -> None:
        self.state = state

    def allowed(self, event: MissionEvent) -> bool:
        return (self.state, event) in TRANSITIONS

    def step(self, event: MissionEvent) -> MissionState:
        key = (self.state, event)
        if key not in TRANSITIONS:
            raise IllegalTransition(f"{self.state.value} cannot handle {event.value}")
        self.state = TRANSITIONS[key]
        return self.state

    def requires_zero_velocity(self) -> bool:
        return self.state in ZERO_VELOCITY_STATES
