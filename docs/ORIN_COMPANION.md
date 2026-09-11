# Orin companion (PR1)

Dry-run mission loop. **Does not arm**, does not open Cube serial, does not
drive servos. Fake camera only.

Install the package into the runtime venv (`.venv`), not only `.venv-dev`:

```bash
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install pyrealsense2   # RealSense USB
.venv/bin/python -m caferoomba preflight --camera fake --vehicle dry-run
.venv/bin/python -m caferoomba preflight --camera realsense --vehicle dry-run
.venv/bin/python -m caferoomba run-companion --camera fake --vehicle dry-run --cycles 12
```

`.venv-dev` is the CPU training env and already has the package.

FSM: `OFF → PRECHECK → HOLD → SWEEP ⇄ TURN → RETURN → IDLE` plus `FAULT`/`ESTOP`.
HOLD/FAULT/ESTOP command zero velocity. Software never calls `arm()`.

Hardware sniffers on this host (USB RealSense D415 + Cube Orange). Never arm:

```bash
.venv/bin/python scripts/capture_realsense.py
.venv/bin/python scripts/capture_cube.py --seconds 5
```

Cube USB is `dialout`. If open fails: `sudo usermod -aG dialout $USER` then log out/in.

PR2 adds KML geofence. PR4 MAVSDK command path. PR5 IMX219 CSI.
