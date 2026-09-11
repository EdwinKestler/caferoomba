# Pending work (priority)

1. Human operator labels for FPV runs in `data/raw/fpv/` (videos are local + GCS).
2. Cosmos teacher: local NIM Docker is **blocked on this 3090 Ti** (see
   `docs/DEPLOYMENT_COSMOS_NIM.md`). Hosted `integrate.api.nvidia.com` needs an
   explicit paid-call approval. Keys exist in `.env`.
3. Approved Colab Enterprise training job (project `flatbox-serverless-demos` exists; no training run yet).
4. Identify the actual Jetson module and JetPack; onboard ONNX/TensorRT loop.
5. Supervised Cube Orange dry-then-hardware plan (no auto-arm).
6. Confirm work/idle durations and charger/dock interfaces.
7. Edwin folder-trust if project Grok hooks/skills should load in new CLI sessions.
