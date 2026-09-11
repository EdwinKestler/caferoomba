---
name: caferoomba-cosmos-teacher
description: Offline NVIDIA Cosmos teacher for CafeRoomba. Use for annotation, mock vs live teacher, NIM model id, or cache keys. Never treat mock output as Cosmos inference. Slash /caferoomba-cosmos-teacher.
---

# Cosmos teacher (offline)

Requested model id: `nvidia/cosmos3-nano-reasoner`. The student must not call this at deploy time.

```bash
.venv-dev/bin/python -c "from caferoomba.teacher.cosmos import annotate, REQUESTED_MODEL_ID; print(REQUESTED_MODEL_ID)"
```

- `backend=mock` always sets `is_mock: true`.
- `backend=live` requires `COSMOS_TEACHER_URL` and `NVIDIA_API_KEY` and is blocked while spending is zero.
- Cache key is model + prompt hash + input hash.

Docs: `docs/DATASET.md`, `docs/MODEL_CARD.md`.
