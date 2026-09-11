"""Optional ArduPilot Rover adapter. Disabled; constructing it does not connect."""

from __future__ import annotations

from caferoomba.control.intents import to_mavlink_yaw_rate
from caferoomba.schemas import Intent


class MavlinkRoverAdapter:
    def __init__(self, *, enabled: bool = False, device: str | None = None) -> None:
        if enabled:
            raise RuntimeError(
                "MAVLink adapter enablement requires explicit owner approval "
                "and is blocked in this CPU milestone"
            )
        self.enabled = False
        self.device = device

    def apply(self, intent: Intent) -> None:
        if not self.enabled:
            raise RuntimeError("MAVLink adapter is disabled; use DryRunAdapter")
        _ = to_mavlink_yaw_rate(intent.yaw_rate_rad_s)
        raise RuntimeError("unreachable: hardware send is not implemented here")
