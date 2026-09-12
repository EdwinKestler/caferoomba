"""Select and exclusively lease one local Cube serial endpoint; never kill users.

The lock coordinates our backends. pyserial also obtains an exclusive device
lock. Other programs must not share the port; use a separately configured
MAVLink router for that architecture. No automatic router/configuration changes.
"""
from __future__ import annotations

import fcntl
import hashlib
from pathlib import Path


def resolve_device(device: str | None) -> str:
    if device:
        path = Path(device)
        if not path.is_absolute() or not str(path).startswith("/dev/") or not path.exists():
            raise ValueError("serial endpoint must be an existing absolute /dev path")
        return str(path)
    directory = Path("/dev/serial/by-id")
    candidates = [p for p in directory.glob("*") if "cube" in p.name.lower()]
    if len(candidates) != 1:
        raise ValueError("select a Cube device explicitly; discovery found zero or multiple")
    return str(candidates[0])


class SerialLease:
    def __init__(self, device: str, lock_dir: Path):
        self.device, self.lock_dir, self._handle = device, lock_dir, None

    def acquire(self):
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(str(Path(self.device).resolve()).encode()).hexdigest()
        handle = (self.lock_dir / (name + ".lock")).open("a+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise RuntimeError("Cube serial endpoint is already leased") from None
        self._handle = handle

    def close(self):
        if self._handle is not None:
            fcntl.flock(self._handle, fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None
