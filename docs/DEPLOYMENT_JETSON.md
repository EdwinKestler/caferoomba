# Jetson Orin deployment

**Target:** owner-confirmed Jetson Orin Nano, Ubuntu Server 22.04 LTS, Python 3.11 project-local `.venv`. **Evidence:** deployment and target acceleration remain unverified in this publication.

## Inventory before installation

Record CPU architecture, kernel, installed NVIDIA board-support/JetPack/L4T stack, camera services, native OpenCV/GStreamer capabilities, CUDA/TensorRT versions, Python ABI and available memory. Do not treat workstation wheels or an Ubuntu release label as a target compatibility check.

Preserve existing `.venv` and system libraries. Use a tested, target-specific dependency manifest. The source adds runtime extras locally; those extras must be merged and verified before relying on them from public `main`.

## Staged deployment

1. Import/configuration checks with no hardware I/O.
2. CPU ONNX replay in `.venv`, using a validated model contract.
3. RealSense and IMX219 tests independently with timestamp/modality reports.
4. Cube telemetry observation under single serial ownership.
5. Combined shadow-mode run and deterministic log review.
6. Target acceleration and numerical/latency checks.
7. Separate approval for motion-capable software and supervised trials.

## Acceleration

Build/verify any TensorRT engine against the target stack. A cloud GPU or x86 engine is not an Orin release artifact. Report the actual execution provider and precision; configuration alone is not evidence of acceleration. Maintain an explicit fallback policy rather than silently changing the backend during a mission.

## Service lifecycle

A future non-root service should name the `.venv` interpreter explicitly, use a controlled working directory, and restart into PRECHECK/HOLD. Camera acquisition and recording must not block independent stop handling. Cloud upload stays outside the control loop. No service installation or automatic boot deployment is included in this documentation publication.

Reference: [TensorRT support matrix](https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/support-matrix.html).
