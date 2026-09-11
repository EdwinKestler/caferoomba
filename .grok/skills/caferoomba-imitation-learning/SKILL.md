---
name: caferoomba-imitation-learning
description: Train and evaluate the CafeRoomba lightweight temporal student on causal FPV clips. Use for dataset splits, CPU smoke training, ONNX export, or human-vs-teacher labels. Slash /caferoomba-imitation-learning.
---

# Imitation learning

Human action labels are primary. Teacher suggestions are auxiliary and never motor commands.

```bash
.venv-dev/bin/python -m caferoomba demo-fixture --workdir artifacts/cpu-smoke
.venv-dev/bin/pytest tests/test_cpu_pipeline.py tests/test_dataset_contracts.py
```

Causal windows end at the decision timestamp. Split by `run_id`. Fixture metrics are software checks only. Docs: `docs/MODEL_CARD.md`.
