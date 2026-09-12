# Colab Enterprise on `flatbox-serverless-demos`

Historical infrastructure snapshot verified 2026-09-11; refresh cloud state before use.

A CPU runtime **was observed running** (2026-09-12 UTC): `kestler-20260911-211649`,
template `caferoomba-cpu`, `e2-standard-4`, `HEALTHY` / `RUNNING`, idle stop
**1 hour**, image **Python 3.12**.

## Verified CPU smoke (owner notebook, 2026-09-12)

On this runtime, after `pip install -e ".[dev,geofence]"`:

- `python -m pytest tests -q` — **46 passed** (Python 3.12)
- `python -m caferoomba demo-fixture` — `"synthetic": true`, `"ok": true`
- Recursive GCS list of `gs://caferoomba/media/data/raw/fpv/` — five `runid00x` source videos plus `clips/part_*.mp4`
- Copied smoke artifacts to `gs://caferoomba/artifacts/colab-cpu-smoke/cpu-smoke/` (`manifest.json`, `student.onnx`, `student.pt`, synthetic frames)

This is **Colab Enterprise CPU execution of the public test/fixture path**. It is not GPU training, Cosmos inference, labeled-FPV learning, or robot motion. Stop the runtime when idle.

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

For the new real-data workflow use [Colab training](COLAB_TRAINING.md) and
notebooks 01–03. The cells below remain historical synthetic smoke instructions,
not the real-FPV training pipeline.

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
