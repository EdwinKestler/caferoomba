"""Heading-validated TURN_180 sub-FSM; no direct actuator calls.

Angles are radians in a left-positive frame. Advancement to the next pass must
be confirmed externally; a heading reversal alone never completes coverage.
Timeouts also cover waiting for clearance and next-pass alignment.
"""
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
    def abort(self):
        """Latch a stopped turn; recovery requires a new validated turn machine."""
        self.state = TurnState.STOP_FAULT

    def __init__(self, *, tolerance_rad=math.radians(8), timeout_s=8.0,
                 retrigger_cooldown_s=4.0):
        if not all(math.isfinite(v) for v in
                   (tolerance_rad, timeout_s, retrigger_cooldown_s)):
            raise ValueError("turn parameters must be finite")
        if not 0 < tolerance_rad < math.pi / 2 or timeout_s <= 0 or retrigger_cooldown_s < 0:
            raise ValueError("invalid turn parameters")
        self.tolerance_rad, self.timeout_s = tolerance_rad, timeout_s
        self.retrigger_cooldown_s = retrigger_cooldown_s
        self.state = TurnState.SWEEP
        self.direction = 1
        self.start_heading = self.target_heading = self.last_heading = 0.0
        self.elapsed_s = self.cooldown_s = self.progress_rad = 0.0

    def trigger(self, heading, direction, *, footprint_clear):
        if self.state != TurnState.SWEEP or self.cooldown_s > 0:
            return self.state
        if not math.isfinite(heading) or direction not in (-1, 1):
            self.state = TurnState.STOP_FAULT
            return self.state
        self.direction, self.start_heading, self.last_heading = direction, heading, heading
        self.target_heading = wrap_pi(heading + direction * math.pi)
        self.elapsed_s = self.progress_rad = 0.0
        self.state = TurnState.TURNING if footprint_clear else TurnState.VERIFY_TURN_CLEARANCE
        return self.state

    def step(self, heading, dt_s, *, footprint_clear, fault=False, alignment_complete=False):
        if fault or not math.isfinite(heading) or not math.isfinite(dt_s) or dt_s < 0:
            self.state = TurnState.STOP_FAULT
        if self.state == TurnState.STOP_FAULT:
            return self.state
        if self.state == TurnState.SWEEP:
            self.cooldown_s = max(0.0, self.cooldown_s - dt_s)
            return self.state
        self.elapsed_s += dt_s
        if self.elapsed_s > self.timeout_s:
            self.state = TurnState.STOP_FAULT
        elif self.state == TurnState.VERIFY_TURN_CLEARANCE:
            if footprint_clear:
                self.last_heading = heading
                self.state = TurnState.TURNING
        elif self.state == TurnState.TURNING:
            delta = wrap_pi(heading - self.last_heading)
            self.last_heading = heading
            self.progress_rad += self.direction * delta
            if not footprint_clear or self.progress_rad < -self.tolerance_rad:
                self.state = TurnState.STOP_FAULT
            elif (self.progress_rad >= math.pi - self.tolerance_rad and
                  abs(heading_error(heading, self.target_heading)) <= self.tolerance_rad):
                self.state = TurnState.ALIGN_ADVANCE_PASS
        elif self.state == TurnState.ALIGN_ADVANCE_PASS:
            if not footprint_clear:
                self.state = TurnState.STOP_FAULT
            elif alignment_complete:
                self.state = TurnState.SWEEP
                self.cooldown_s = self.retrigger_cooldown_s
        return self.state
