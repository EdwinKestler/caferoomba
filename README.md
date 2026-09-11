# CafeRoomba

Coffee-bean drying-patio sweeper for Edwin Kestler. Historical keyboard/GPIO
rover code is preserved under `rover/`. The new AI path is a **CPU-first**
offline teacher + onboard student pipeline in `src/caferoomba/`.

License: see `LICENSE` (original project license unchanged).

## Status (2026-09-11)

| Path | Evidence |
|---|---|
| CPU fixture: clips → mock teacher → train → eval → ONNX → dry-run | `tested_offline` (synthetic) |
| Live NVIDIA Cosmos | `blocked` (no authorized endpoint/key) |
| Colab Enterprise | `blocked` (no approved project/budget) |
| Jetson / TensorRT | `blocked` (this host is not a Jetson) |
| Hardware / Cube Orange send | `blocked` (adapter disabled) |

Do not read fixture metrics as Cosmos inference, Google Cloud training, Jetson
deployment, or autonomous robot performance.

## Diagrams

Training (offline): causal FPV clips + human labels [+ reviewed Cosmos auxiliaries] → small temporal policy.

Onboard: recent FPV frames → student ONNX → typed intent → fail-closed supervisor → dry-run (MAVLink later).

## Quickstart (CPU, isolated env)

```bash
python3 scripts/bootstrap.py          # prints the plan
python3 scripts/bootstrap.py --apply  # creates .venv-dev only
.venv-dev/bin/python -m pip install -e ".[dev]"
.venv-dev/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv-dev/bin/python -m pip install onnx onnxruntime
.venv-dev/bin/python scripts/doctor.py
.venv-dev/bin/pytest tests -q
.venv-dev/bin/python -m caferoomba demo-fixture --workdir artifacts/cpu-smoke
```

Do **not** install `rover/requirements.txt` into this environment.

## Agents

Project Memory v2.5 is mandatory: `AGENTS.md`, `docs/PROJECT_MEMORY.md`.
Challenge skills: `.grok/skills/caferoomba-*`.

## Limitations

Open-loop timed turns in the legacy rover are not learned visual 180s.
No real FPV dataset is in git. Work/idle times (1800/1200 s) are unconfirmed drafts.
