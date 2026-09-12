# Runtime and shadow-mode integration

## Choose the correct source state

The current checkout contains the portable companion runtime described in
[PORTABLE_RUNTIME.md](PORTABLE_RUNTIME.md). Git status and the checked-out source
determine availability; historical publication hashes are not runtime configuration.

Use `.venv/bin/python` for runtime work. Keep `.venv-dev` for training. Inspect `git status`, the actual configuration classes, and CLI help before assuming a feature is present.

## Public no-hardware check

```bash
.venv/bin/python -m pip check
.venv/bin/python -m caferoomba run-companion --help
.venv/bin/python -m caferoomba run-companion --camera fake --vehicle dry-run --cycles 12
```

The package and dependencies must already be installed in `.venv`. No ONNX path means the baseline STOP policy; that is not inference from a trained model.

## Runtime configuration

The implementation has `camera`, `vehicle`, `fence`, `policy` and `loop` sections.
Portable profiles use fake/RealSense/USB-UVC cameras and dry-run or serial-passive
vehicles. IMX219/Argus remains an optional Jetson-specific backend. MAVSDK is a
legacy observation option without authoritative vehicle health; it remains
fail-closed. All vehicle paths are non-actuating. Healthy real-camera profiles
stay HOLD; stale observations or unhealthy vehicle state enter FAULT.

Set map selection, exclusions and clearance explicitly. Set camera temporal sampling to match the model contract. Configure a stable serial path and expected system identity. Use a private run directory under `artifacts/` for recorded images and telemetry.

## CLI reporting

The CLI reports observed arming state, simulation/shadow status, fault reasons,
and recording location. FAULT/ESTOP produces `ok: false` and exit 1. Use
`--camera-device`, `--vehicle-device`, `--policy`, and `--record-dir` to override
the selected profile. A completed run is not evidence of autonomous operation.

## USB observations

The repository has `scripts/capture_realsense.py` and `scripts/capture_cube.py`. Read their current implementation before use; identify devices and check permissions. The former is a still capture, not a synchronized demonstration recorder. The latter is not a command adapter. Neither script proves complete autonomy or operational safety.

A MAVSDK observation connection may exchange protocol traffic. Use the dedicated passive serial path when a strictly application-receive-only test is required. Never let two adapters independently open the Cube USB port.

## Stop and recovery

On a missing map, stale observation, camera error or telemetry fault, hold/fault and record the reason. Recover explicitly after revalidation. Do not substitute a random camera, guessed position, stale heading or legacy GPIO controller.
