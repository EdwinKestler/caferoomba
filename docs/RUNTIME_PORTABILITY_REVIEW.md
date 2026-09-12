# Runtime portability review — 2026-09-12

Scope: the rover runtime, not the training pipeline. Supported entrypoint:
`python -m caferoomba run-companion`. See [deployment instructions](PORTABLE_RUNTIME.md).

## Implemented

- Composition-based camera, vehicle and policy adapters; mission and turn FSMs.
- USB UVC and serial-selected RealSense profiles; explicit stable Cube device.
- Passive Cube telemetry for heartbeat/health, GPS, heading, magnetic readings,
  sensor masks, rangefinder and reported servo outputs, with freshness checks.
- Unknown/unhealthy vehicle and stale camera inputs fail closed; interrupted
  turns latch STOP. Unknown footprint clearance cannot authorize movement.
- Bounded histories and recorder lifecycle, process-isolated UVC acquisition,
  startup cleanup, finite mission inputs and atomic single-writer patch updates.
- Configurable ONNX providers with explicit fallback policy; no training
  framework required in the deployment environment.
- Legacy GPIO executable entrypoints disabled before hardware imports.
- Ubuntu 22.04 / Python 3.11 runtime CI job added, not dispatched by this review.

## Local verification

Host: Ubuntu 24.04 x86-64, Python 3.11.15. This is not an Orin result.
Regression checks passed: 84 tests in the development environment, including
the existing CPU fixture test; 64 runtime-only tests in the environment without
PyTorch. No training source was changed. Runtime dependency checks, scoped Ruff,
byte-compilation and `git diff --check` passed. A 30-cycle fake-camera/dry-run
simulation reached SWEEP with `ok: true` and zero physical commands.
Both camera profiles ran through the actual companion loop with passive Cube
serial telemetry for 30 cycles each. Recordings were complete with zero drops,
zero commands and no cleanup errors. The UVC profile was rerun after adding
process isolation, again completing 30 cycles with clean teardown.

The Cube supplied a fresh heartbeat but reported MAV_STATE_CRITICAL (5), so
the supervisor correctly remained FAULT with `vehicle_unhealthy`. Disarmed
state was observed; no arming, mode changes or actuator commands were sent.
GPS was unavailable. RAW_IMU magnetic readings and servo output telemetry were
observed; port 1 reported 1500 microseconds. This does not prove movement,
compass calibration or working steering. No rangefinder observation was received.
RealSense supplied RGB/depth; the webcam supplied RGB only. They were tested
separately, not as simultaneous fused policy inputs.

Local evidence (ignored artifacts, not publication assets):

- RealSense: `artifacts/shadow-runs/20260912T171922-8a674502/manifest.json`
- UVC process isolation: `artifacts/shadow-runs/20260912T172254-e8c6ab48/manifest.json`

## Remaining deployment gates

Verify native ARM64/Python 3.11 dependencies on the actual Ubuntu 22.04 Orin:
RealSense SDK, OpenCV and the chosen ONNX accelerator provider. Run the same
regression suite and representative model latency/output checks there. CPU
inference with a synthetic checkpoint establishes software wiring only.

All vehicle implementations remain non-actuating. Physical driving requires
a separately reviewed Cube command adapter, command expiry/watchdog, operator
stop, healthy/calibrated sensors, clearance validation, SITL and controlled trials.
Matching advertised TOPS alone is not a portability acceptance test.
