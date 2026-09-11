#!/usr/bin/env python3
"""Non-destructive environment report. Never prints secret values."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from caferoomba.environment import report  # noqa: E402


def main() -> None:
    print(json.dumps(report(), indent=2))


if __name__ == "__main__":
    main()
