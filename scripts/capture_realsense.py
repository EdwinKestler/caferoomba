#!/usr/bin/env python3
"""Grab one RealSense D4xx color (and depth) still. Never talks to the Cube.

Run with the runtime venv:

    .venv/bin/python scripts/capture_realsense.py
    .venv/bin/python -m caferoomba capture-realsense
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from caferoomba.perception.realsense import RealSenseCamera  # noqa: E402


def capture(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cam = RealSenseCamera(width=640, height=480)
    cam.open()
    try:
        sample = cam.read()
    finally:
        cam.close()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    color_path = out_dir / f"realsense_color_{stamp}.png"
    Image.fromarray(sample.color).save(color_path)
    depth_path = None
    if sample.depth is not None:
        depth = sample.depth
        if depth.max() > 0:
            scaled = (depth.astype("float32") / depth.max() * 255.0).astype("uint8")
        else:
            scaled = depth.astype("uint8")
        depth_path = out_dir / f"realsense_depth_{stamp}.png"
        Image.fromarray(scaled).save(depth_path)
    report = {
        "ok": True,
        "source": sample.source,
        "usb_type": getattr(cam, "usb_type", None),
        "stream": getattr(cam, "stream", None),
        "color": str(color_path),
        "depth": str(depth_path) if depth_path else None,
        "frame_shape": list(sample.color.shape),
        "has_depth": sample.depth is not None,
        "armed": False,
    }
    (out_dir / "realsense_capture.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts" / "hw-capture",
        help="directory for PNG stills (gitignored under artifacts/)",
    )
    args = parser.parse_args()
    report = capture(args.out)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
