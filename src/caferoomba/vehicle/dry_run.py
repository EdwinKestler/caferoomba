"""Dry-run vehicle: records intents, never opens serial/GPIO, never arms."""

from __future__ import annotations

from caferoomba.control.adapters.dry_run import DryRunAdapter
from caferoomba.schemas import Intent, SafetyDecision
from caferoomba.vehicle.client import TelemetrySnapshot


class DryRunVehicle:
    """Wraps DryRunAdapter. ``connect()`` does not touch /dev/ttyACM*."""

    def __init__(self) -> None:
        self._adapter = DryRunAdapter()
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def close(self) -> None:
        self._connected = False

    def telemetry(self) -> TelemetrySnapshot:
        return TelemetrySnapshot(
            heartbeat_ok=True,
            vehicle_health_ok=True,
            gps_ok=False,
            armed=False,
            mode="DRY_RUN",
            is_synthetic=True,
        )

    def send_intent(self, intent: Intent, **safety_kwargs) -> SafetyDecision:
        if not self._connected:
            raise RuntimeError("DryRunVehicle.send_intent before connect()")
        return self._adapter.apply(intent, **safety_kwargs)

    def arm(self) -> None:
        raise RuntimeError("software never arms the vehicle")

    @property
    def sent(self):
        return self._adapter.sent
