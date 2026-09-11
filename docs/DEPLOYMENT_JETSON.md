# Jetson deployment

Status: `planned` / `blocked` on this host.

The development machine is x86_64 with a GeForce RTX 3090 Ti. It is **not**
Jetson Nano, AGX Xavier, or another L4T module (`/etc/nv_tegra_release` absent).

CPU ONNX export/replay is `tested_offline`. Do not treat that as TensorRT or
Jetson evidence. Build engines on the actual JetPack stack. Do not overwrite
vendor OpenCV/CUDA/TensorRT with generic wheels. An x86 or L4 engine is not
portable to Nano/Xavier.
