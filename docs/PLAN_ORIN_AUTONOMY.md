# Plan: Orin Nano companion + Cube Orange Mini + cameras

Status: PR1 **implemented** (`tested_offline` dry-run + fake camera). Later
PRs remain `planned`. No arming, no pigpio drive, no Jetson PWM.

Target vehicle computer: **Jetson Orin Nano, Ubuntu 22.04** (Server/Core
certified). Companion code in a Python 3.11 `.venv`. Traction/servos stay on
the **Cube Orange Mini (ArduPilot Rover)** over USB CDC (`/dev/ttyACM*`).
This x86 host may dry-run the same code with a USB RealSense and an optional
Cube; it is not the Orin.

## 1. What we keep vs what we stop using

Keep (rewrite into modules, do not import as-is):

- KML/KMZ geofence parse + Shapely point-in-polygon from
  `docs/legacy code/rover_gpt.py`
- MAVSDK serial connect pattern (`serial:///dev/ttyACM0:…`) as one vehicle
  backend
- Existing `src/caferoomba` intents, fail-closed `supervise()`, TURN_180
  machine, mission timers, patch store, ONNX student, dry-run adapter
- Historical `rover/` pigpio keyboard stack **as museum code only**

Stop using on Orin:

- Jetson/Pi GPIO `Servo` / `pigpio` / `roverservo` for drive or steering
- Auto-`arm()` from `rover_gpt.py` / telemetry scripts
- Duplicate `getch()` + outer FSM actuation
- Open-loop `sleep()` as a substitute for heading/GPS

Fix while porting geofence: `rover_gpt.py` stores ring vertices as `(lat, lon)`
then builds `Point(lon, lat)` against that polygon — Shapely x/y must be
**longitude, latitude** consistently.

## 2. Target `src/` layout

Reorder so **runtime** (Orin loop) is separate from **training** (host/Colab):

```text
src/caferoomba/
  app/                 # process entry, config, FSM runner
    fsm.py             # MissionFsm (table-driven)
    loop.py            # timed cycle: sense → policy → supervise → act
    config.py          # YAML/env: ports, cameras, speeds, KML path
  perception/
    camera.py          # CameraSource protocol
    realsense.py       # USB D4xx color+depth
    csi_imx219.py      # Orin MIPI CSI-2 (nvargus/libcamera/V4L2)
    buffer.py          # causal frame stack for the student
  policy/
    onboard.py         # ONNX Runtime (CPU now, TensorRT later on Orin)
  geofence/
    kml.py             # KMZ/KML via pykml; lon/lat normalized
    fence.py           # Shapely Polygon; fail-closed if missing/invalid
  vehicle/
    client.py          # VehicleClient protocol (no hardware in ctor)
    dry_run.py         # move current DryRunAdapter here
    mavsdk_rover.py    # MAVSDK serial; GUIDED/Rover setpoints; no auto-arm
    pymavlink_rover.py # optional second backend
    telemetry.py       # heartbeat, GPS, heading, mode (read-only until armed)
  control/             # keep: intents, safety, turn180, mission, patch_store
  data/ learning/ teacher/   # keep: offline training path on .venv-dev
```

`caferoomba.cli` grows `run-companion` (dry-run default) and `preflight`.

Training stays importable; the Orin loop must not import `torch` training or
Cosmos.

## 3. Finite state machine (mission)

One explicit table, OOP, no hidden transitions. Sub-machine for TURN_180
already exists; the mission FSM **calls** it, it does not replace it.

```text
OFF
  → PRECHECK     (cameras, Cube heartbeat, GPS if required, load KML)
  → HOLD         (disarmed; operator may arm via RC/GCS — software never arms)
  → SWEEP        (policy intents if supervisor allows and inside fence)
  → TURN         (TURN_180 sub-FSM; still geofenced)
  → SWEEP
  → RETURN       (RTL / hold heading toward home — ArduPilot RTL if configured)
  → IDLE         (work timer done; wait idle_wake_s)
  → FAULT        (any fail-closed reason)
  → ESTOP        (operator stop / RC kill; PWM remains Cube failsafe)
```

`HOLD` and `FAULT` send **zero velocity** intents only. Leaving `HOLD` requires
`heartbeat_ok`, `geofence_ok` (or “fence not required” config), and
`observation_age_ms` fresh. Software never calls `action.arm()`.

## 4. Data flow (one cycle, ~10–30 Hz)

1. **Sense** — RealSense color (+ depth if available) and/or IMX219; Cube
   heartbeat, GPS, heading via MAVSDK.
2. **Buffer** — last N FPV frames, causal, PTS/monotonic time.
3. **Policy** — ONNX student → `{LEFT,STRAIGHT,RIGHT,STOP}` + turn180 score.
   Missing camera ⇒ `required_sensor_missing`.
4. **Geofence** — current lat/lon vs Shapely polygon; outside or no fix ⇒
   `geofence_ok=False`.
5. **Intent** — typed `Intent` (body frame, left-positive yaw). Expiry ~100–250 ms.
6. **Supervise** — existing `supervise()` plus fence, heartbeat, stale frames,
   Cube mode not GUIDED/AUTO if we are commanding.
7. **Act** — dry-run log, or Rover setpoint through MAVSDK (`velocity` /
   `Attitude` as documented for **ArduPilot Rover**, not Copter takeoff).
   Adapter converts yaw sign to NED.

Depth from RealSense feeds `footprint_clear` (coarse; not a certified LiDAR
geofence). IMX219 is FPV backup or second stream, not mixed into one tensor
until calibrated.

## 5. Vehicle / Cube Orange Mini

- USB appears as `/dev/ttyACM0` (or ACM1). Baud in config; legacy used
  **19200** — verify in ArduPilot `SERIAL` params (USB often 115200). Do not
  guess on hardware.
- `VehicleClient.connect()` is explicit; constructors stay inert (tests).
- Telemetry-only mode is the default on this x86 box even if a Cube is
  plugged in.
- Command mode (`send_intent`) requires `CAFEROOMBA_ALLOW_VEHICLE_COMMANDS=1`
  **and** a CLI flag. Still no arm.
- Do not drive ESCs from the Jetson.

## 6. Cameras

| Sensor | Bus | Role |
|---|---|---|
| Intel RealSense | USB | Primary FPV color for policy; depth → clearance |
| IMX219 | 22-pin MIPI CSI-2 | Orin-only FPV/alternate; V4L2/nvargus behind `CsiCamera` |
| `/dev/video*` on this host | V4L2 | Dev stub if RealSense SDK missing |

`pyrealsense2` is **not** importable on system Python here; install it in
**`.venv`** (user-requested inference env), not `.venv-dev` (CPU training).

Abstract `CameraSource.read()` → `FrameSet{color, depth|None, t_ms}`.

## 7. Environments

| Env | Machine | Role |
|---|---|---|
| `.venv-dev` | this x86 host | CPU train/ONNX/pytest (already) |
| `.venv` | this host **and** Orin | runtime: onnxruntime, mavsdk, shapely, pykml, pyrealsense2 |
| JetPack stack | Orin only | later `onnxruntime-gpu` / TensorRT; do not pip-overwrite CUDA |

`pyproject.toml` extra: `orin = ["mavsdk", "shapely", "pykml", "lxml"]` and
optional `realsense` extra. Never install `rover/requirements.txt`.

Local inference test (this machine):

```bash
source .venv/bin/activate
python -m caferoomba preflight --camera realsense --vehicle dry-run
python -m caferoomba run-companion --policy artifacts/cpu-smoke/student.onnx --vehicle dry-run
```

Cube plugged in, still dry-run until the env flag is set:

```bash
python -m caferoomba preflight --vehicle mavsdk --device /dev/ttyACM0
```

## 8. Documentation and tests (required with the code)

- Module docstrings: purpose, thread/async model, hardware side effects.
- `docs/ORIN_COMPANION.md` — ports, baud, camera indexes, FSM diagram.
- Tests (no hardware):
  - KML lon/lat order + inside/outside + missing file fail-closed
  - FSM legal/illegal transitions
  - Camera protocol fake source → causal buffer
  - Supervisor geofence + lost heartbeat
  - MAVSDK adapter mock (no serial)
- Hardware tests marked `@pytest.mark.hardware` and skipped unless
  `CAFEROOMBA_HARDWARE=1`.

## 9. Implementation PRs (order)

1. **Layout + FSM skeleton** — new packages, `MissionFsm`, config YAML,
   dry-run loop with fake camera. No Cube.
2. **Geofence** — port/fix KML/KMZ+Shapely; wire `geofence_ok` into
   `supervise()`.
3. **Cameras** — RealSense in `.venv` on this host; CSI stub that fails
   clearly off-Orin; causal buffer into ONNX `OnboardPolicy`.
4. **MAVSDK vehicle client** — connect/heartbeat/GPS read-only; command
   path behind flags; baud/device config; no arm.
5. **Orin extras** — IMX219, docs, JetPack notes, TensorRT as follow-up
   (not required to close the FSM loop).

## 10. Non-goals (this plan)

- Local Cosmos NIM on 3090 Ti (already blocked)
- Colab training
- pigpio on Orin
- Automatic arming or mode changes to ARMED
- Claiming patio coverage from policy accuracy

## Key decisions

1. **Cube owns PWM**; Jetson is companion only.
2. **Software never arms.**
3. **Split `.venv` (runtime) vs `.venv-dev` (CPU train).**
4. **Mission FSM + existing TURN_180 sub-FSM**, table-driven.
5. **MAVSDK first** (matches `rover_gpt.py`); pymavlink optional.
6. **RealSense primary** on USB; IMX219 Orin-only behind the same protocol.
7. **Fail closed** if KML missing, GPS stale, camera stale, or heartbeat lost.
