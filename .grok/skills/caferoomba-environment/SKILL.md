---
name: caferoomba-environment
description: Inspect CafeRoomba local environment, isolated .venv-dev, and doctor reports. Use for bootstrap, dependency, GPU/CPU, Jetson vs host, or credential-presence questions. Slash /caferoomba-environment.
---

# Environment

Run from the repo root. Do not install `rover/requirements.txt`. Do not use sudo.

```bash
python3 scripts/bootstrap.py            # dry-run plan
python3 scripts/doctor.py
.venv-dev/bin/python -m caferoomba doctor
```

Create `.venv-dev` only (`scripts/bootstrap.py --apply`). Report credential **booleans**, never values. Host GPU presence is not Jetson evidence. Details: `docs/AGENT_SETUP.md`.
