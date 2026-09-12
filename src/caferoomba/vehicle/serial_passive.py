"""Passive Cube serial receiver plus a dry-run intent sink.

pyserial owns the port exclusively. The MAVLink parser has no output sink;
this backend never writes MAVLink bytes, requests streams, arms, changes mode,
or sends actuator commands. Constructors do not acquire devices.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from caferoomba.vehicle.dry_run import DryRunVehicle
from caferoomba.vehicle.serial_link import SerialLease, resolve_device
from caferoomba.vehicle.telemetry import TelemetryCache


class PassiveSerialVehicle(DryRunVehicle):
    def __init__(
        self,
        config,
        *,
        lock_dir: Path | None = None,
        serial_factory=None,
        parser_factory=None,
    ):
        super().__init__()
        if config.allow_commands:
            raise RuntimeError("vehicle commands are not enabled")
        self.config = config
        self.cache = TelemetryCache(system_id=config.system_id,
                                    heartbeat_timeout_ms=config.heartbeat_timeout_ms,
                                    gps_timeout_ms=config.gps_timeout_ms)
        self.lock_dir = lock_dir or Path(".caferoomba/serial-locks")
        self.serial_factory = serial_factory
        self.parser_factory = parser_factory
        self._port = self._thread = self._lease = None
        self._stop = threading.Event()
        self.commands_sent = 0

    def connect(self):
        if self._connected or self._port is not None:
            raise RuntimeError("Cube already connected")
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("previous Cube receiver is still stopping")
        # A connection attempt is a new link epoch. Never let a previous
        # heartbeat event, cached sample, receiver error, or stop flag satisfy it.
        self._thread = None
        self._stop.clear()
        self.cache.reset()
        device = resolve_device(self.config.device)
        self._lease = SerialLease(device, self.lock_dir)
        self._lease.acquire()
        try:
            factory = self.serial_factory
            if factory is None:
                import serial

                factory = serial.Serial
            self._port = factory(device, baudrate=self.config.baud, timeout=0.1,
                                 write_timeout=0.1, exclusive=True)
            parser_factory = self.parser_factory
            if parser_factory is None:
                from pymavlink.dialects.v20 import ardupilotmega

                parser_factory = ardupilotmega.MAVLink
            self._parser = parser_factory(None)
            self._parser.robust_parsing = True
            self._thread = threading.Thread(target=self._receive,
                                             name="caferoomba-cube", daemon=True)
            self._thread.start()
            ready = self.cache.ready.wait(self.config.connect_timeout_s)
            error = self.cache.error
            if not ready or error:
                raise TimeoutError(error or "no ArduPilot Rover heartbeat before deadline")
            self._connected = True
        except Exception:
            self.close()
            raise

    def _receive(self):
        try:
            while not self._stop.is_set():
                data = self._port.read(4096)
                if not data:
                    continue
                for msg in self._parser.parse_buffer(data) or []:
                    self.cache.ingest(msg.get_type(), msg.to_dict(),
                                      system_id=msg.get_srcSystem(),
                                      component_id=msg.get_srcComponent(),
                                      received_at_ms=int(time.monotonic() * 1000))
        except Exception as exc:
            # close() intentionally interrupts the receiver; do not turn that
            # expected shutdown race into a persistent link error.
            if not self._stop.is_set():
                self.cache.set_error(
                    f"serial receive failed: {type(exc).__name__}: {exc}"
                )

    def telemetry(self):
        return self.cache.snapshot(int(time.monotonic() * 1000))

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        if self._port is not None:
            self._port.close()
            self._port = None
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1)
        if self._thread is not None and self._thread.is_alive():
            # The receiver may still hold or access the endpoint. Preserve the
            # lease so no second controller can acquire it concurrently.
            raise RuntimeError("passive Cube receiver did not stop; lease is retained")
        if self._thread is not None and not self._thread.is_alive():
            self._thread = None
        if self._lease is not None:
            self._lease.close()
            self._lease = None
        self._connected = False
