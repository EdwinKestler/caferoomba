---
name: caferoomba-rover-safety
description: CafeRoomba fail-closed supervisor, dry-run adapter, TURN_180 machine, and mission persistence. Use for STOP, stale observations, yaw-sign, Cube Orange, or arming questions. Slash /caferoomba-rover-safety.
---

# Safety

Never arm hardware. Default adapter is dry-run. MAVLink stays disabled.

Body yaw is left-positive; ArduPilot NED yaw is opposite (`to_mavlink_yaw_rate`).

```bash
.venv-dev/bin/pytest tests/test_safety_and_turn.py
```

TURN_180 is a trigger plus a pivot; a 180° spin does not change coverage rows. Docs: `docs/SAFETY.md`.
