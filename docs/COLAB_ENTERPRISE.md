# Colab Enterprise on `flatbox-serverless-demos`

Verified 2026-09-11. Billing is on.

A **CPU runtime is running** (2026-09-12 UTC): `kestler-20260911-211649`,
template `caferoomba-cpu`, `e2-standard-4`, `HEALTHY` / `RUNNING`, idle stop
**1 hour**, image **Python 3.12**. That is a live notebook VM, not a completed
training job. Stop it in the console when idle to avoid Compute charges.

## What is enabled

| Item | Status |
|---|---|
| Project | `flatbox-serverless-demos` |
| Region | `us-central1` |
| APIs | Vertex AI / Agent Platform (`aiplatform`), Dataform, Compute Engine, Notebooks |
| IAM | `kestler@flatbox.co` is Owner plus `roles/aiplatform.colabEnterpriseUser` and `colabEnterpriseAdmin` |
| CPU template | `caferoomba-cpu` (`e2-standard-4`, 100 GB PD, idle stop 1 h) |
| GPU template | `gpu-template` (`g2-standard-4` + 1× L4) — **billable when started** |

## Open a notebook

1. [Colab Enterprise notebooks](https://console.cloud.google.com/agent-platform/colab/notebooks?project=flatbox-serverless-demos)
2. Region: **us-central1**
3. **New notebook**
4. Connect to a runtime. Prefer **caferoomba-cpu** unless you explicitly need a GPU.
5. First connect: grant the console access to your Google user credentials.

Do not start `gpu-template` unless you accept L4 GPU charges. Stop runtimes when idle.

## CLI

```bash
gcloud config set project flatbox-serverless-demos
gcloud config set colab/region us-central1
gcloud colab runtime-templates list --region=us-central1
gcloud colab runtimes list --region=us-central1
```

Creating a runtime from a template (starts billing):

```bash
gcloud colab runtimes create --runtime-template=caferoomba-cpu --region=us-central1
```

## CPU notebook cells (caferoomba-cpu)

Install **dev + geofence** extras or pytest collection fails on `pykml`:

```python
%cd /content/caferoomba
!pip install -e ".[dev,geofence]"
!pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
!pip install onnx onnxruntime
!python -m pytest tests -q
!python -m caferoomba demo-fixture --workdir /tmp/cpu-smoke
!gcloud storage ls --recursive gs://caferoomba/media/data/raw/fpv/
!gcloud storage cp -r /tmp/cpu-smoke gs://caferoomba/artifacts/colab-cpu-smoke/
```

`demo-fixture` succeeding with `"synthetic": true` is a software smoke test, not FPV training.
A non-recursive `gsutil ls` only shows run folders; use `gcloud storage ls --recursive` to see objects.
