# Local companion integration status

Published software revision: `cd0bb2d485831c6b040f933d7ee87ca22b2569f8`,
including portable-runtime revision
`db7caec2f0a2d3ae95a692e65c7dedfddc85933c`.

Working machine for the recorded hardware observations: `andorxps` (x86_64),
not the Jetson Orin.

## Software closure

Roadmap Stage 1 is closed at the `implemented` / `tested_offline` level. CPU CI
[run 34710087792](https://github.com/EdwinKestler/caferoomba/actions/runs/34710087792)
succeeded at `cd0bb2d` in both the Ubuntu 22.04/Python 3.11 portable-runtime job
and the Ubuntu 24.04 full-suite job. The local training implementation record at
that revision reports 110 passing tests. These results do not constitute an
Orin, navigation or physical-motion test.

## Host-only passive USB evidence

The portable-runtime review records separate 30-cycle companion-loop runs with
RealSense and UVC cameras plus passive Cube serial telemetry. The adapters sent
zero commands. The Cube heartbeat was fresh but reported a critical vehicle
state, so fail-closed supervision correctly remained in FAULT. The observations
do not establish synchronized demonstration capture, camera/Cube clock
calibration, GPS, compass calibration, steering, clearance or movement.

Vehicle backends remain non-actuating. Software does not arm, change mode, write
PWM or send motion. The serial-passive backend parses received bytes only;
MAVSDK observation mode can send protocol traffic. Real-camera runtime profiles
remain HOLD unless fail-closed checks move them to FAULT.

## Remaining integration gates

- Record synchronized FPV, reviewed human commands and Cube state with calibrated
  timestamp mapping and provenance.
- Run the current notebooks on the reviewed real dataset in the selected Colab
  runtime; do not relabel the historical CPU fixture smoke as real-data training.
- Validate native ARM64 dependencies, camera support, ONNX/TensorRT parity and
  latency on the actual Orin.
- Implement and review command expiry/watchdog and operator authority, then pass
  navigation replay/SITL before any separately authorized physical trial.
- Demonstrate sweeping, return and docking closed-loop; none is current evidence.
