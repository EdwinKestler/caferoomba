# Challenge evidence

Contest pathway (user-reported): “Intro to Inference: How to Run AI Models on a
GPU”. This repository does **not** claim three pathways or Cosmos fine-tuning.

| Area | This milestone |
|---|---|
| Innovation | Offline teacher / onboard student split; typed intents; fail-closed supervisor |
| NVIDIA / Google Cloud | CPU PyTorch+ONNX tested offline. Keys in local `.env`. Private GCS media at `gs://caferoomba/media/`. Local Cosmos3-Reasoner NIM Docker **blocked** (24 GiB 3090 Ti vs >56 GiB / 48 GiB FP8). Hosted NIM API not called |
| Usefulness | Software path for bean-patio sweeping; no physical trial |
| Documentation | Audit, architecture, dataset, model, safety, pending work |

Machine-readable pointer: `docs/evidence/manifest.json`.
Skills and MCP setup are agent tooling, not robot NVIDIA/GCP integration.
