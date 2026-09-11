"""VehicleClient protocol. ``connect()`` is explicit; ``arm()`` is forbidden."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from caferoomba.schemas import Intent, SafetyDecision


@dataclass
class TelemetrySnapshot:
    heartbeat_ok: bool
    gps_ok: bool = False
    heading_deg: float | None = None
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    armed: bool = False
    mode: str | None = None


class VehicleClient(Protocol):
    def connect(self) -> None:
        """Open the link. Dry-run is a no-op."""

    def close(self) -> None: ...

    def telemetry(self) -> TelemetrySnapshot: ...

    def send_intent(self, intent: Intent, **safety_kwargs) -> SafetyDecision: ...

    def arm(self) -> None:
        """Must raise. Companion software never arms."""
