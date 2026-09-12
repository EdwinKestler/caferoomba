# Quickstart

Start on a workstation with no robot connected. The public baseline uses synthetic fixtures and dry-run actions. This guide does not authorize arming or motion.

## 1. Inspect the checkout

```bash
git status --short
git log -1 --format='%H %s'
python3 --version
```

Use Python 3.11 for the documented development/runtime path. Preserve uncommitted work. Existing project environments must not be deleted or replaced without review.

## 2. CPU training fixture

```bash
python3 scripts/bootstrap.py
python3 scripts/bootstrap.py --apply
.venv-dev/bin/python -m pip install -e '.[dev]'
.venv-dev/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv-dev/bin/python -m pip install onnx onnxruntime
.venv-dev/bin/python -m pytest tests -q
.venv-dev/bin/python -m caferoomba demo-fixture --workdir artifacts/cpu-smoke
```

The output manifest describes a **synthetic software smoke test**. It does not demonstrate Cosmos inference, learning from real FPV demonstrations, cloud training, or robot navigation. Pin the successfully tested dependency environment for longer-term reproduction; the existing bootstrap commands are not a universal lockfile.

## 3. Runtime environment

Use `<repo>/.venv/bin/python` explicitly for inference. On Edwin's workstation the checkout is `/home/kestl/github/caferoomba`. The Orin uses its own project-local environment.

```bash
.venv/bin/python -c 'import sys, platform; print(sys.executable); print(sys.version); print(platform.machine())'
.venv/bin/python -m pip check
.venv/bin/python -m caferoomba run-companion --camera fake --vehicle dry-run --cycles 12
```

The final command requires the package installed in `.venv` and uses no USB camera. On a fresh workstation, create `.venv` with an explicitly selected Python 3.11 interpreter and install the package. Install runtime libraries only after inspecting the target. Do not apply generic x86 GPU wheels to a Jetson.

## 4. Before a physical camera or Cube

Read [Runtime](ORIN_COMPANION.md), [Hardware](HARDWARE.md), and [Safety](SAFETY.md). Public and local integration CLI behavior differ. No `--policy` or serial-backend flag should be assumed to exist: inspect `python -m caferoomba run-companion --help` in the actual checkout.

Never run `docs/legacy code/rover_gpt.py` as a setup test. It contains automatic arming and legacy actuator behavior. Do not install `rover/requirements.txt` into the modern runtime.
