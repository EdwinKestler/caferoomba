# Runtime and shadow-mode integration

## Choose the correct source state

**Public baseline:** `eb9a2a4` has a fake-camera/dry-run companion skeleton and USB inspection tools. **Local integration:** uncommitted workstation changes on `feat/orin-shadow-integration` add geofencing, shadow-mode composition, stricter perception contracts, passive serial/MAVSDK observation, and recording. This documentation/site publication does not merge that code.

Use `.venv/bin/python` for runtime work. Keep `.venv-dev` for training. Inspect `git status`, the actual configuration classes, and CLI help before assuming a feature is present.

## Public no-hardware check

```bash
.venv/bin/python -m pip check
.venv/bin/python -m caferoomba run-companion --help
.venv/bin/python -m caferoomba run-companion --camera fake --vehicle dry-run --cycles 12
```

The package and dependencies must already be installed in `.venv`. No ONNX path means the baseline STOP policy; that is not inference from a trained model.

## Local integration configuration (not a public-baseline recipe)

The local implementation has `camera`, `vehicle`, `fence`, `policy` and `loop` configuration sections. It supports fake/RealSense/IMX219 camera interfaces; dry-run, serial-passive and MAVSDK observation backends; and a configured ONNX path. All vehicle paths remain non-actuating. Real-camera profiles remain HOLD.

Set map selection, exclusions and clearance explicitly. Set camera temporal sampling to match the model contract. Configure a stable serial path and expected system identity. Use a private run directory under `artifacts/` for recorded images and telemetry.

## Known CLI limitation

The local `cli.py` was not fully refactored during the preceding implementation session. Its old top-level `ok`/`armed` summary is not an authoritative statement of Cube state or per-cycle safety. Do not advertise unimplemented flags such as `--policy`. Verify actual help and inspect detailed runtime records. CLI completion and tests are a pending milestone.

## USB observations

The repository has `scripts/capture_realsense.py` and `scripts/capture_cube.py`. Read their current implementation before use; identify devices and check permissions. The former is a still capture, not a synchronized demonstration recorder. The latter is not a command adapter. Neither script proves complete autonomy or operational safety.

A MAVSDK observation connection may exchange protocol traffic. Use the dedicated passive serial path when a strictly application-receive-only test is required. Never let two adapters independently open the Cube USB port.

## Stop and recovery

On a missing map, stale observation, camera error or telemetry fault, hold/fault and record the reason. Recover explicitly after revalidation. Do not substitute a random camera, guessed position, stale heading or legacy GPIO controller.
