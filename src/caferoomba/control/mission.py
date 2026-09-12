"""Configurable work/idle mission. Defaults are unconfirmed drafts, not measured."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class MissionConfig:
    work_s: float = 1800.0  # unconfirmed draft
    idle_wake_s: float = 1200.0  # unconfirmed draft
    confirmed: bool = False

    def __post_init__(self):
        if not all(math.isfinite(v) and v > 0 for v in (self.work_s, self.idle_wake_s)):
            raise ValueError("mission durations must be finite and positive")


class MissionScheduler:
    def __init__(self, config: MissionConfig | None = None) -> None:
        self.config = config or MissionConfig()
        self.active = False
        self.elapsed_s = 0.0
        self.idle_s = 0.0

    def start(self) -> None:
        if self.active:
            raise RuntimeError("refusing overlapping mission")
        self.active = True
        self.elapsed_s = 0.0
        self.idle_s = 0.0

    def step(self, dt_s: float, *, charging_required: bool = False) -> str:
        if not math.isfinite(dt_s) or dt_s < 0:
            raise ValueError("mission timestep must be finite and nonnegative")
        if charging_required and self.active:
            self.active = False
            return "paused_charging"
        if self.active:
            self.elapsed_s += dt_s
            if self.elapsed_s >= self.config.work_s:
                self.active = False
                self.idle_s = 0.0
                return "work_complete"
            return "working"
        self.idle_s += dt_s
        if self.idle_s >= self.config.idle_wake_s:
            if charging_required:
                return "idle_blocked_charging"
            self.start()
            return "woke"
        return "idle"
