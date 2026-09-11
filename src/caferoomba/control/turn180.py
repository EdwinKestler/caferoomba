"""TURN_180 is a trigger, not a continuous motor command."""

from __future__ import annotations

import math
from enum import Enum


class TurnState(str, Enum):
    SWEEP = "SWEEP"
    VERIFY_TURN_CLEARANCE = "VERIFY_TURN_CLEARANCE"
    TURNING = "TURNING"
    ALIGN_ADVANCE_PASS = "ALIGN_ADVANCE_PASS"
    STOP_FAULT = "STOP_FAULT"


def wrap_pi(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def heading_error(current: float, target: float) -> float:
    return wrap_pi(target - current)


class Turn180Machine:
    def __init__(
        self,
        *,
        tolerance_rad: float = math.radians(8),
        timeout_s: float = 8.0,
        retrigger_cooldown_s: float = 4.0,
    ) -> None:
        self.tolerance_rad = tolerance_rad
        self.timeout_s = timeout_s
        self.retrigger_cooldown_s = retrigger_cooldown_s
        self.state = TurnState.SWEEP
        self.direction = 1
        self.start_heading = 0.0
        self.target_heading = 0.0
        self.elapsed_s = 0.0
        self.cooldown_s = 0.0
        self.progress_rad = 0.0

    def trigger(self, heading: float, direction: int, *, footprint_clear: bool) -> TurnState:
        if self.state != TurnState.SWEEP:
            return self.state
        if self.cooldown_s > 0:
            return self.state
        self.direction = 1 if direction >= 0 else -1
        self.start_heading = heading
        self.target_heading = wrap_pi(heading + self.direction * math.pi)
        self.elapsed_s = 0.0
        self.progress_rad = 0.0
        self.state = (
            TurnState.VERIFY_TURN_CLEARANCE if not footprint_clear else TurnState.TURNING
        )
        if not footprint_clear:
            self.state = TurnState.VERIFY_TURN_CLEARANCE
        else:
            self.state = TurnState.TURNING
        return self.state

    def step(
        self,
        heading: float,
        dt_s: float,
        *,
        footprint_clear: bool,
        fault: bool = False,
    ) -> TurnState:
        if fault:
            self.state = TurnState.STOP_FAULT
            return self.state
        if self.state == TurnState.SWEEP:
            self.cooldown_s = max(0.0, self.cooldown_s - dt_s)
            return self.state
        if self.state == TurnState.VERIFY_TURN_CLEARANCE:
            if footprint_clear:
                self.state = TurnState.TURNING
            return self.state
        if self.state == TurnState.TURNING:
            if not footprint_clear:
                self.state = TurnState.STOP_FAULT
                return self.state
            self.elapsed_s += dt_s
            self.progress_rad = abs(heading_error(self.start_heading, heading))
            if self.elapsed_s > self.timeout_s:
                self.state = TurnState.STOP_FAULT
                return self.state
            if abs(heading_error(heading, self.target_heading)) <= self.tolerance_rad:
                self.state = TurnState.ALIGN_ADVANCE_PASS
            return self.state
        if self.state == TurnState.ALIGN_ADVANCE_PASS:
            # A 180 pivot retraces the same line; caller must command a lateral offset.
            self.state = TurnState.SWEEP
            self.cooldown_s = self.retrigger_cooldown_s
            return self.state
        return self.state
