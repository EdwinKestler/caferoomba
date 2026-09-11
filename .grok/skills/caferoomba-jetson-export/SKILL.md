---
name: caferoomba-jetson-export
description: Export and replay CafeRoomba ONNX on CPU; prepare Jetson/TensorRT steps without claiming device evidence. Use for ONNX, TensorRT, JetPack, or edge runtime questions. Slash /caferoomba-jetson-export.
---

# Export

CPU ONNX replay is implemented. TensorRT engines must be built on the target Jetson; this host is x86_64.

```bash
.venv-dev/bin/python -m caferoomba demo-fixture
```

Do not copy an L4/x86 engine to Nano/Xavier. Do not install a newer TensorRT over JetPack. Docs: `docs/DEPLOYMENT_JETSON.md`.
