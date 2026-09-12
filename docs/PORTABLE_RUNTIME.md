# Portable rover runtime

The supported entrypoint is `python -m caferoomba run-companion`. The historical
`rover/` GPIO prototype is not the deployable runtime. Training and cloud teacher
code are outside this runtime and are not required to start it.

## Ownership and composition

| Responsibility | Interface / implementation |
| --- | --- |
| Mission transitions | `MissionFsm`, hosted by `CompanionLoop` |
| Turn proposal verification | `Turn180Machine` sub-FSM |
| USB image acquisition | `CameraSource`: RealSense or UVC `UsbCamera` |
| Temporal input | `CausalFrameBuffer`, shared RGB preprocessing |
| Local prediction | STOP baseline or ONNX `OnboardPolicy` |
| Vehicle observations | `VehicleClient`, passive Cube serial receiver |
| Actuator ownership | Cube/ArduPilot; companion physical output remains disabled |
| Logs | Bounded asynchronous `RunRecorder`, local artifacts |

The companion does not use SBC GPIO/PWM/I2C pins for steering or peripherals.
Executable historical `rover/` modules fail immediately before importing GPIO
libraries; their source remains as an archive. `docs/legacy code/` is historical
material and must never be executed as the runtime.
GPS, compass, rangefinder and servo observations arrive through Cube MAVLink,
with freshness and missing values preserved. Attitude is a fused estimate, not
proof of a healthy calibrated magnetometer. Reported servo PWM is not evidence
that a servo moved. Range observations are not complete footprint clearance.

RealSense supplies RGB and depth; the UVC webcam supplies RGB only. Each run
selects one policy viewpoint explicitly. Run them separately against the same
Cube to validate interchangeability; do not concatenate different viewpoints
into a trained temporal buffer. The legacy IMX219/Argus adapter is optional and
Jetson-specific, never a dependency of USB profiles.

UVC acquisition runs in a spawned child process with a bounded frame queue.
This avoids relying on OpenCV read-timeout settings unsupported by V4L2 and
allows bounded teardown of a stalled native read. RealSense uses SDK deadlines
and a latest-frame worker. Missing or stale frames fault even during warmup.
Neither host-side mechanism replaces a Cube-side actuator watchdog.

Patch persistence validates finite coordinates and atomically replaces its
JSON file before updating memory. It is single-writer storage, not a concurrent
mission database or a guarantee against power-loss filesystem failures.

## Ubuntu 22.04 and Python 3.11

Use an existing verified Python 3.11 installation to create an isolated runtime
environment on the target. Do not replace Ubuntu's system Python or mix its
Python 3.10 native extensions into Python 3.11.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[runtime,autopilot,usb-camera,geofence]'
# Only when using RealSense; check target ARM64/Python 3.11 SDK availability:
.venv/bin/python -m pip install -e '.[realsense]'
.venv/bin/python -m pip check
.venv/bin/python -m caferoomba run-companion --cycles 12
```

Do not recreate an existing `.venv`; inspect it first. ARM64 native dependencies
must have matching wheels or be built for the installed target ABI. USB access
also needs host device permissions and a supported kernel/SDK. Comparable TOPS
alone does not establish model/operator support or measured latency.

ONNX defaults to `CPUExecutionProvider`. Set ordered
`policy.execution_providers` for the installed accelerator. Unavailable or
unexpected providers fail startup. CPU node fallback is allowed only when
explicitly listed. No automatic model download or cloud inference is performed.
Reported provider registration is not proof all nodes executed on that device;
profile and compare representative outputs and latency on each replacement SBC.
TensorRT engines require target-specific validation; Python 3.11 compatibility
cannot be inferred solely from the Ubuntu/JetPack version.

## Host and hardware checks

CPU simulation uses the same composition root, FSM and supervisor:

```bash
.venv/bin/python -m caferoomba run-companion --cycles 30
```

Inspect `/dev/serial/by-id/` and `/dev/v4l/by-id/` locally. Copy the example
profiles and replace the device placeholders; never guess a serial interface.

```bash
.venv/bin/python -m caferoomba run-companion \
  --config config/realsense-shadow.yaml \
  --vehicle-device /dev/serial/by-id/YOUR_CUBE_IF00 --cycles 50

.venv/bin/python -m caferoomba run-companion \
  --config config/webcam-shadow.yaml \
  --vehicle-device /dev/serial/by-id/YOUR_CUBE_IF00 \
  --camera-device /dev/v4l/by-id/YOUR_WEBCAM_VIDEO_INDEX0 --cycles 50
```

Use `--policy path/to/student.onnx` for local inference; without it the policy
is deterministic STOP. A synthetic fixture checkpoint validates software only.
The runtime acquires the Cube exclusively, listens without sending MAVLink
commands, and records observations. No arming, mode changes or PWM commands.
No-GPS bench tests can omit the geofence; they establish no navigation accuracy.

Real hardware stays HOLD unless a fault moves it to FAULT. A fresh heartbeat
and healthy vehicle are separate facts; a CRITICAL heartbeat must produce
`vehicle_unhealthy`. CLI `ok: false`/exit 1 is then the expected result, even
when USB access is successful. Inspect `armed_observed`, `simulation`, reasons
and the recording path. Unknown arming state is not reported as disarmed.

## Remaining physical operation gates

The portable observation/simulation path is executable. Physical driving still
requires a separately tested command adapter, Cube-side command expiry/watchdog,
operator stop authority, sensor/clearance checks, Rover SITL and supervised trials.
USB read deadlines cannot make an unresponsive native driver or Python inference
thread a certified stop controller. The current Cube has no GPS attached; a
port-1 servo bench connection does not establish steering geometry or safe motion.

Reference: [ONNX execution providers](https://onnxruntime.ai/docs/execution-providers/).
