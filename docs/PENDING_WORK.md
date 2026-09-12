# Roadmap and acceptance gates

This roadmap is an implementation order, not a delivery promise or a statement of production readiness.

| Stage | Work | Acceptance evidence |
|---|---|---|
| 1. Finish local integration | CLI output/flags, cleanup/failure paths, dependency manifests, final regression | Full named-revision suite and logs; no unrelated source changes merged implicitly |
| 2. Real observations | Synchronized FPV, human commands, Cube state, calibration and timestamp mapping | Recorded run with provenance and synchronization diagnostics; no actuation |
| 3. Full-data learning | Strict split handling, minibatch iteration and held-out evaluation | All training examples used; no fallback into test data; reproducible reports |
| 4. Cosmos teacher | Authorized provider adapter, reviewed annotations, masked auxiliary losses | Actual request/response provenance and student ablation |
| 5. Cloud execution | Colab Enterprise is usable on `flatbox-serverless-demos` ([setup](COLAB_ENTERPRISE.md)); run student training/evaluation | Executed job/notebook, dataset/model hashes and redacted environment record |
| 6. Navigation integration | Complete path/footprint checks, patch approach, turn connector and next-pass verification | Deterministic replay and Rover simulation, including failure cases |
| 7. Target deployment | Orin native-camera compatibility, ONNX/acceleration parity and latency | Device-specific measurements; no desktop evidence relabelled as Orin |
| 8. Supervised physical work | Command adapter, independent watchdog, operator authority, safe return | Explicitly approved trials with interventions, errors and safety observations recorded |
| 9. Docking and repeat missions | Dock/contact/charging confirmation, energy readiness, serviced-patch memory | Closed-loop mission evidence rather than a GPS arrival or timer alone |

## Decisions still requiring measurement or confirmation

Brush/robot footprint; steering and pivot capability; usable depth coverage; localization accuracy; safe speeds and braking distance; work/idle intervals; dock interface; temporal camera sampling; exact deployed native software stack.

More skills or MCP servers are not the current bottleneck. The bottleneck is connecting real data, validated learning, safe runtime state, and device evidence.
