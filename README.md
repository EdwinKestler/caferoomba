# CafeRoomba

**Physical AI for the coffee-drying patio.** An open-source robotics project by **Edwin Kestler** exploring how human demonstrations can become visual navigation policies for a coffee-bean sweeping rover.

[Project website](https://edwinkestler.github.io/caferoomba/) · [Documentation](docs/README.md) · [Quickstart](docs/QUICKSTART.md) · [Evidence & status](docs/STATUS.md)

## What the project does

The application is **redistributing coffee beans on drying patios**, not vacuuming discarded grounds. The intended mission is to find a coffee patch, sweep adjacent passes, remember the serviced region, and return to a charging station. The historical physical prototype and the newer learned-policy implementation are separate evidence tracks.

**Current public software:** a CPU-first pipeline for synthetic clips, a mock teacher, lightweight student training, evaluation, ONNX export, and dry-run decisions. The public baseline also includes a companion FSM and USB inspection scripts. It does **not** establish learned autonomous navigation on the Orin.

| Workstream | Evidence boundary |
|---|---|
| Historical rover | Owner-provided historical prototype media; not a demonstration of the 2026 learned controller |
| Public CPU baseline | Synthetic training/export/replay tested; 26-test baseline passed locally and public CI succeeded |
| Local Orin integration | Separate, uncommitted workstation work; 13 focused tests passed during the prior implementation session; final regression pending |
| Live Cosmos / Colab Enterprise | No verified inference or training run in this publication |
| Jetson deployment / motion / docking | Targeted or planned; not validated by desktop CPU tests |

See [STATUS.md](docs/STATUS.md) for revisions, provenance, and limitations. The website/documentation publication does not merge the local runtime changes.

## Architecture

```text
Offline development
FPV demonstrations + synchronized human controls
  → [planned: reviewed Cosmos annotations]
  → small temporal navigation policy → evaluation → ONNX

Onboard target
RGB history → student → typed intent → independent safety validation
  → Cube/ArduPilot navigation interface → actuators

Current public execution: dry-run only; no autonomous motion commands.
```

Cosmos is intended as an **offline teacher**. The deployed student must not require cloud credentials or live Cosmos responses.

## Start without hardware

```bash
python3 scripts/bootstrap.py          # Inspect the proposed isolated setup
python3 scripts/bootstrap.py --apply  # Create .venv-dev
.venv-dev/bin/python -m pip install -e '.[dev]'
.venv-dev/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv-dev/bin/python -m pip install onnx onnxruntime
.venv-dev/bin/python -m pytest tests -q
.venv-dev/bin/python -m caferoomba demo-fixture --workdir artifacts/cpu-smoke
```

Use the project-local **`.venv` with Python 3.11 for runtime/inference**. Keep training in `.venv-dev`; do not install `rover/requirements.txt` into either new environment. Native Jetson dependencies require target-specific verification. [Runtime instructions](docs/ORIN_COMPANION.md).

## Hardware target

Jetson Orin Nano, Ubuntu Server 22.04 LTS, project-local Python 3.11 `.venv`; Cube Orange Mini running ArduPilot over USB virtual serial; Intel RealSense over USB; IMX219 over CSI. The Cube owns actuator outputs. The development workstation is not the Jetson. [Hardware matrix](docs/HARDWARE.md).

## Contribute safely

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SAFETY.md](docs/SAFETY.md), and [SECURITY.md](SECURITY.md). Do not auto-arm, execute legacy GPIO scripts, expose credentials, or publish private raw datasets. Agents must follow [AGENTS.md](AGENTS.md) and the existing [Project Memory protocol](docs/PROJECT_MEMORY.md).

## License and attribution

Original **GNU Affero General Public License, version 3** text is preserved in [LICENSE](LICENSE). Model weights, SDKs, dependencies, and contributed media retain their respective terms. Project media supplied by Edwin Kestler is identified in [MEDIA.md](docs/MEDIA.md).

Independent project. NVIDIA and Google Cloud names describe technology and community-learning context; no endorsement, award, or production certification is claimed.

## This Experiment

[Explore the experiment](https://edwinkestler.github.io/caferoomba/#experiment), [watch the two looping dataset previews](https://edwinkestler.github.io/caferoomba/#data-clips), and read [the local-notebook / Colab Enterprise workflow](docs/EXPERIMENT.md). Both public clip derivatives are below 9 MB; originals remain unchanged.

Human demonstration → FPV video → **Google Cloud Colab Enterprise** → Cosmos physical reasoning → lightweight learned navigation policy → NVIDIA Jetson → Cube Orange → robot motion. This is the proposed architecture; cloud execution and field validation are separate milestones.
