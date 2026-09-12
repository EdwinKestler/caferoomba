"""Optional MAVSDK telemetry integration, extracted conceptually from rover_gpt.

Observation-only, NOT zero-transmit: MAVSDK may send discovery/subscription
traffic. No Action/Offboard API is used. For strict passive capture use the
serial-passive backend. SDK link state is not a measured heartbeat timestamp.
The SDK-owned process cleanup is isolated to this version-pinned adapter.
"""
from __future__ import annotations
import asyncio
import math
import socket
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path
from caferoomba.vehicle.client import TelemetrySnapshot
from caferoomba.vehicle.dry_run import DryRunVehicle
from caferoomba.vehicle.serial_link import SerialLease, resolve_device


class MavsdkTelemetryVehicle(DryRunVehicle):
    def __init__(self, config, *, lock_dir=None, grpc_port=50151, system_factory=None):
        super().__init__()
        if config.allow_commands:
            raise RuntimeError("MAVSDK vehicle commands are not enabled")
        self.config, self.grpc_port, self.system_factory = config, grpc_port, system_factory
        self.lock_dir = lock_dir or Path(".caferoomba/serial-locks")
        self._stop, self._ready = threading.Event(), threading.Event()
        self._lock = threading.Lock()
        self._state = TelemetrySnapshot(heartbeat_ok=False)
        self._thread = self._lease = None
        self._error = None
        self.commands_sent = 0
        self._gps_fix = False
        self._gps_t_ms = None

    def connect(self):
        self.device = resolve_device(self.config.device)
        self._lease = SerialLease(self.device, self.lock_dir)
        self._lease.acquire()
        # Refuse an occupied RPC port rather than attach to another running SDK.
        probe = socket.socket()
        try:
            probe.bind(("127.0.0.1", self.grpc_port))
        except OSError:
            self._lease.close()
            raise RuntimeError("MAVSDK RPC port is already in use") from None
        finally:
            probe.close()
        self._thread = threading.Thread(target=self._run, name="caferoomba-mavsdk", daemon=True)
        self._thread.start()
        if not self._ready.wait(self.config.connect_timeout_s) or self._error:
            self.close()
            raise RuntimeError(self._error or "MAVSDK connection deadline exceeded")
        self._connected = True

    def _run(self):
        try:
            asyncio.run(self._observe())
        except Exception as exc:
            self._error = str(exc)
            self._ready.set()

    async def _consume(self, source, kind):
        async for value in source:
            now = int(time.monotonic() * 1000)
            with self._lock:
                if kind == "connection":
                    self._state.heartbeat_ok = bool(value.is_connected)
                    if value.is_connected:
                        self._ready.set()
                elif kind == "position":
                    self._state.latitude_deg, self._state.longitude_deg = value.latitude_deg, value.longitude_deg
                    self._state.position_t_ms = now
                elif kind == "gps":
                    self._gps_fix = value.fix_type.value >= 3
                    self._gps_t_ms = now
                elif kind == "heading":
                    self._state.heading_deg, self._state.heading_t_ms = value.heading_deg, now
                elif kind == "armed":
                    self._state.armed = bool(value)
                elif kind == "mode":
                    self._state.mode = str(value)

    async def _observe(self):
        from mavsdk import System
        system = (self.system_factory or System)(port=self.grpc_port)
        tasks = []
        try:
            await asyncio.wait_for(system.connect(system_address=f"serial://{self.device}:{self.config.baud}"),
                                   timeout=self.config.connect_timeout_s)
            streams = [(system.core.connection_state(), "connection"),
                       (system.telemetry.position(), "position"),
                       (system.telemetry.gps_info(), "gps"),
                       (system.telemetry.heading(), "heading"),
                       (system.telemetry.armed(), "armed"),
                       (system.telemetry.flight_mode(), "mode")]
            tasks = [asyncio.create_task(self._consume(source, kind)) for source, kind in streams]
            while not self._stop.is_set():
                for task in tasks:
                    if task.done():
                        raise RuntimeError("MAVSDK telemetry stream ended") from task.exception()
                await asyncio.sleep(0.05)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            # MAVSDK 3.17.2 exposes no public close(). Reap ONLY this System's child.
            process = getattr(system, "_server_process", None)
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)
                system._server_process = None

    def telemetry(self):
        now = int(time.monotonic() * 1000)
        with self._lock:
            state = replace(self._state)
        state.link_error = self._error
        state.heartbeat_ok = state.heartbeat_ok and self._error is None
        state.gps_ok = (self._gps_fix and self._gps_t_ms is not None and
                        0 <= now - self._gps_t_ms <= self.config.gps_timeout_ms and
                        state.position_t_ms is not None and
                        0 <= now - state.position_t_ms <= self.config.gps_timeout_ms and
                        state.latitude_deg is not None and state.longitude_deg is not None and
                        math.isfinite(state.latitude_deg) and math.isfinite(state.longitude_deg) and
                        -90 <= state.latitude_deg <= 90 and -180 <= state.longitude_deg <= 180)
        if not state.gps_ok:
            state.latitude_deg = state.longitude_deg = None
        if state.heading_t_ms is None or now - state.heading_t_ms > self.config.gps_timeout_ms:
            state.heading_deg = None
        return state

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.config.connect_timeout_s + 3)
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("MAVSDK worker did not stop; lease is retained")
        if self._lease is not None:
            self._lease.close()
        self._connected = False
