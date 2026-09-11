#!/usr/bin/env python3
"""Read-only MAVLink listen on the Cube Orange USB CDC port.

Never arms, never changes mode, never sends RC/PWM. HEARTBEAT and telemetry
only. Requires membership in the dialout group to open /dev/ttyACM*.

    .venv/bin/python scripts/capture_cube.py
    .venv/bin/python -m caferoomba capture-cube --seconds 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_DEVICE = "/dev/serial/by-id/usb-Hex_ProfiCNC_CubeOrange_280044000C51393239383638-if00"
INTERESTING = {
    "HEARTBEAT",
    "SYS_STATUS",
    "GPS_RAW_INT",
    "GLOBAL_POSITION_INT",
    "ATTITUDE",
    "VFR_HUD",
    "STATUSTEXT",
    "POWER_STATUS",
    "MEMINFO",
}


def _msg_to_dict(msg) -> dict:
    payload = msg.to_dict()
    payload.pop("mavpackettype", None)
    header = getattr(msg, "_header", None)
    return {
        "type": msg.get_type(),
        "sysid": header.srcSystem if header else None,
        "compid": header.srcComponent if header else None,
        "fields": payload,
    }


def capture(*, device: str, baud: int, seconds: float, out_dir: Path) -> dict:
    from pymavlink import mavutil

    out_dir.mkdir(parents=True, exist_ok=True)
    conn = mavutil.mavlink_connection(
        device,
        baud=baud,
        autoreconnect=False,
        source_system=255,
        source_component=190,
    )
    try:
        hb = conn.wait_heartbeat(timeout=10)
        if hb is None:
            raise TimeoutError(f"no HEARTBEAT on {device} @ {baud}")
        started = time.monotonic()
        rows = [_msg_to_dict(hb)]
        while time.monotonic() - started < seconds:
            msg = conn.recv_match(blocking=True, timeout=1)
            if msg is None:
                continue
            name = msg.get_type()
            if name in INTERESTING or name == "HEARTBEAT":
                rows.append(_msg_to_dict(msg))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_path = out_dir / f"cube_mavlink_{stamp}.jsonl"
        with log_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        types = sorted({row["type"] for row in rows})
        armed = None
        for row in rows:
            if row["type"] == "HEARTBEAT" and "base_mode" in row["fields"]:
                armed = bool(row["fields"]["base_mode"] & 128)
        report = {
            "ok": True,
            "device": device,
            "baud": baud,
            "seconds": seconds,
            "message_count": len(rows),
            "types": types,
            "log": str(log_path),
            "armed_observed": armed,
            "commands_sent": [],
            "arm_attempted": False,
        }
        (out_dir / "cube_capture.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts" / "hw-capture")
    args = parser.parse_args()
    try:
        report = capture(
            device=args.device,
            baud=args.baud,
            seconds=args.seconds,
            out_dir=args.out,
        )
    except (PermissionError, OSError) as exc:
        if getattr(exc, "errno", None) not in {13, None} and "Permission" not in str(exc):
            raise
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"cannot open Cube USB CDC: {exc}",
                    "device": args.device,
                    "hint": "sudo usermod -aG dialout $USER  (then log out/in)",
                    "arm_attempted": False,
                },
                indent=2,
            )
        )
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
