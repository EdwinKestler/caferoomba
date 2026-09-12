# Roadmap and acceptance gates

This roadmap is an implementation order, not a delivery promise or a statement
of production readiness. A closed implementation gate does not close its later
data, cloud, target-device or physical-validation gates.

| Stage | Status | Work / acceptance evidence |
|---|---|---|
| 1. Finish local integration | **Closed — `implemented` / `tested_offline`** | Portable runtime revision `db7caec` is included in `cd0bb2d`; CPU CI run 34710087792 passed both the Ubuntu 22.04/Python 3.11 runtime job and Ubuntu 24.04 full suite. No hardware-performance claim |
| 2. Real observations | **Partial** | Passive RealSense, UVC and Cube observations were recorded on the x86_64 host with zero commands. Still required: synchronized FPV, reviewed human commands, Cube state, calibration and timestamp mapping with provenance and diagnostics |
| 3. Full-data learning | **Implementation closed — not real-data trained** | Strict preparation/splits, all-example minibatch iteration, resume, validation-only selection, held-out evaluation and representative ONNX export are implemented and tested with generated/synthetic inputs. Run the owner's reviewed dataset to produce real metrics |
| 4. Cosmos teacher | **Open / live path `blocked`** | Authorized provider request/response provenance, human-reviewed annotations, explicit masked auxiliary losses and a student ablation |
| 5. Cloud execution | **Open for current real-data pipeline** | Follow [Real FPV Colab training](COLAB_TRAINING.md). Execute notebooks 01–03 with reviewed data, preserving dataset/model hashes, notebook revision and a redacted environment record. Historical CPU fixture smoke does not satisfy this gate |
| 6. Navigation integration | **Open** | Complete path/footprint checks, patch approach, turn connector and next-pass verification in deterministic replay and Rover simulation, including failures |
| 7. Target deployment | **Open** | Verify native-camera dependencies and ONNX/TensorRT output parity and latency on the actual Orin ARM64/Python 3.11 environment; desktop and x86 CI are not Orin evidence |
| 8. Supervised physical work | **Open** | Separately reviewed command adapter, independent expiry/watchdog, operator authority and safe return; explicitly approved trials must record interventions, errors and safety observations |
| 9. Docking and repeat missions | **Open** | Dock/contact/charging confirmation, energy readiness and serviced-patch memory demonstrated closed-loop; GPS arrival or a timer alone is insufficient |

## Decisions still requiring measurement or confirmation

Brush/robot footprint; steering and pivot capability; usable depth coverage;
camera/Cube/command clock calibration; localization accuracy; safe speeds and
braking distance; work/idle intervals; dock interface; temporal camera sampling;
and the exact native Orin/TensorRT software stack.

More skills or MCP servers are not the current bottleneck. The bottleneck is
reviewed synchronized data, executed learning, safe navigation/command behavior,
and target-device and physical evidence.
