#!/usr/bin/env python3
"""Idempotent local bootstrap. Default is plan/dry-run. Never touches system Python."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv-dev"


def run(command: list[str]) -> int:
    print("+", " ".join(command))
    return subprocess.call(command, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="create .venv-dev and install CPU extras",
    )
    args = parser.parse_args()
    plan = [
        "create isolated .venv-dev with Python 3.11 if missing",
        "install caferoomba[cpu,dev] into .venv-dev only",
        "do not install rover/requirements.txt",
        "do not modify .venv or system site-packages",
    ]
    print("bootstrap plan:")
    for item in plan:
        print("-", item)
    if not args.apply:
        print("dry-run only; pass --apply to execute")
        return 0
    if not VENV.exists():
        code = run(["uv", "venv", str(VENV), "--python", "3.11"])
        if code:
            return code
    code = run(["uv", "pip", "install", "--python", str(VENV), "-e", f"{ROOT}[dev]"])
    if code:
        return code
    print("applied. activate with: source .venv-dev/bin/activate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
