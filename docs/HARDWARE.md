# Hardware and environments

## Owner-confirmed target

| Component | Intended interface | Responsibility |
|---|---|---|
| NVIDIA Jetson Orin Nano | Local compute | Camera processing, student inference, mission logic, supervision |
| Ubuntu Server 22.04 LTS | Host operating system | Native drivers and service lifecycle |
| Python 3.11 `.venv` | Project-local environment | Application and inference isolation |
| Cube Orange Mini / ArduPilot | USB virtual serial | Navigation/vehicle state and all actuator outputs |
| Intel RealSense | USB | Primary RGB and depth acquisition |
| IMX219 | 22-pin MIPI CSI-2 camera connector | Target-specific alternate/additional view |
| GNSS and vehicle sensors | Cube telemetry | Position, heading and health, subject to configured freshness/quality |

`andorxps` is the x86_64 development workstation, **not the Orin**. A package import or camera test there does not establish Jetson deployment. Earlier Nano/AGX Xavier references should not be reused as the current target identity.

Ubuntu certification, board support, JetPack/L4T, kernel, CUDA/TensorRT, camera drivers and Python ABI are separate facts. Record the installed stack rather than deriving it from the Ubuntu release alone. [NVIDIA camera documentation](https://docs.nvidia.com/jetson/archives/r36.4.4/DeveloperGuide/SD/CameraDevelopment/CameraSoftwareDevelopmentSolution.html).

## USB rules

Prefer an explicitly configured `/dev/serial/by-id/` path; do not assume `/dev/ttyACM0` is stable. Identify the connected Cube, firmware and MAVLink system ID. Do not kill another application to free a port. Only one process owns the physical serial link; optional routing must preserve one motion-command authority.

RealSense acquisition must report the actual stream profile and USB mode. Infrared diagnostics are not equivalent to RGB inference. Raw depth requires its depth scale and calibration. A forward camera does not prove complete clearance for a pivot or reverse movement.

## Environment isolation

| Environment | Role |
|---|---|
| `.venv-dev` | CPU learning, export and development tests |
| `.venv` | Runtime inference and camera/telemetry integration tests |
| `.caferoomba/site-venv` | Optional isolated website build tooling, not robot runtime |

Do not install the historical GPIO requirements into the modern environments. Keep Jetson-native libraries compatible with the installed board stack. An x86 TensorRT engine is not an Orin deployment artifact.

## Bring-up record

Record architecture, OS, kernel, board identity, Python path/version, package inventory, model hash, camera profile, native timestamp domain, Cube identity/firmware, and test command. Do not publish device serial numbers, exact deployment coordinates or credentials in public reports.
