#!/usr/bin/env python3
"""Write unlabeled controls.jsonl + labels.jsonl for a short FPV run.

Does not invent LEFT/STRAIGHT/RIGHT/STOP. Training must ignore status=unlabeled.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

VIDEO = "video-ae5e8a55-14f8-4564-8c6d-2955eef4474a.mp4"
SHA256 = "e6af93be3c431efbf630e0c0055b1b208254d59a55848729f0cd997b80eda4cf"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="runid001")
    parser.add_argument("--duration-ms", type=int, default=10042)
    parser.add_argument("--control-period-ms", type=int, default=250)
    parser.add_argument("--segment-ms", type=int, default=2370)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or Path("data/raw/fpv") / args.run_id
    out.mkdir(parents=True, exist_ok=True)

    controls = []
    t = 0
    while t <= args.duration_ms:
        controls.append(
            {
                "schema_version": "caferoomba.controls.v1",
                "run_id": args.run_id,
                "t_ms": t,
                "command": None,
                "status": "unlabeled",
                "source": "draft_template",
                "notes": "Fill command: w/a/s/d/x or LEFT/STRAIGHT/RIGHT/STOP. Do not leave unlabeled in training.",
            }
        )
        t += args.control_period_ms

    labels = []
    part = 1
    end = args.segment_ms
    while end < args.duration_ms:
        labels.append(
            {
                "schema_version": "caferoomba.labels.v1",
                "run_id": args.run_id,
                "decision_timestamp_ms": end,
                "window_start_ms": end - args.segment_ms,
                "window_end_ms": end,
                "clip_path": f"clips/part_{part:02d}.mp4",
                "video_path": VIDEO,
                "video_sha256": SHA256,
                "viewpoint": None,
                "action": None,
                "turn180_onset": None,
                "turn180_direction": None,
                "label_source": None,
                "reviewer": None,
                "status": "unlabeled",
                "is_synthetic": False,
                "notes": (
                    "Watch the clip that ends at this PTS. Set viewpoint to FPV or EXTERNAL. "
                    "Set action to LEFT|STRAIGHT|RIGHT|STOP. Set turn180_onset true only at the start of a 180."
                ),
            }
        )
        part += 1
        end += args.segment_ms
    labels.append(
        {
            "schema_version": "caferoomba.labels.v1",
            "run_id": args.run_id,
            "decision_timestamp_ms": args.duration_ms,
            "window_start_ms": max(0, args.duration_ms - args.segment_ms),
            "window_end_ms": args.duration_ms,
            "clip_path": f"clips/part_{part:02d}.mp4",
            "video_path": VIDEO,
            "video_sha256": SHA256,
            "viewpoint": None,
            "action": None,
            "turn180_onset": None,
            "turn180_direction": None,
            "label_source": None,
            "reviewer": None,
            "status": "unlabeled",
            "is_synthetic": False,
            "notes": "Last shard. Same fill rules as other rows.",
        }
    )

    cpath = out / "controls.jsonl"
    lpath = out / "labels.jsonl"
    cpath.write_text("".join(json.dumps(row) + "\n" for row in controls), encoding="utf-8")
    lpath.write_text("".join(json.dumps(row) + "\n" for row in labels), encoding="utf-8")
    print(json.dumps({"controls": str(cpath), "n_controls": len(controls), "labels": str(lpath), "n_labels": len(labels)}))


if __name__ == "__main__":
    main()
