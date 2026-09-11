# Cosmos 3 Reasoner NIM — local Docker evaluation

Evaluated 2026-09-11 on this development host. **Not deployed.** This is not
Cosmos inference evidence.

Official image from NVIDIA’s Linux+Docker instructions:

```text
nvcr.io/nim/nvidia/cosmos3-reasoner:latest
-e NIM_MODEL_SIZE=nano   # serves nvidia/cosmos3-nano-reasoner
```

The catalog curl test talks to `http://127.0.0.1:8000/v1/chat/completions`.

## Host vs NVIDIA support matrix (VLM NIM 1.7.0)

| Requirement | This host | Cosmos3-Nano (8B) official |
|---|---|---|
| GPU | GeForce RTX 3090 Ti, **24 GiB**, CC **8.6** | Generic BF16: **>56 GiB**. FP8: CC **≥ 8.9** (Ada). Named floor: L40S **48 GiB FP8** |
| Disk | **~30 GiB free** on `/` | **20–30 GiB** container+weights |
| RAM | 60 GiB total, ~17 GiB available | NIM often wants a large host RAM headroom |
| Docker | 29.x, `nvidia` runtime in daemon.json | Required |
| NGC key | `NVIDIA_API_KEY` in local `.env`; `NGC_API_KEY` aliased | `docker login nvcr.io` + `-e NGC_API_KEY` |

Verdict: **do not `docker run` this NIM on the 3090 Ti.** It is below the
published VRAM floor, cannot use the FP8 profile (CC 8.6 < 8.9), and a pull
would consume most remaining disk.

Super (32B) is further out of reach.

## What would work later

- A **48 GiB+ Ada/Hopper** GPU (L40S FP8, RTX PRO 6000, H100, …) **and**
  **≥40 GiB free disk**, then:
  `./scripts/cosmos_nim_preflight.sh` must exit 0 before any pull.
- Until then, keep the teacher on **mock** for tests, or use the **hosted**
  NVIDIA API (`COSMOS_TEACHER_URL=https://integrate.api.nvidia.com/v1`) only
  after an explicit paid-call approval. Hosted calls are not local NIM
  evidence.

## Commands we did **not** run

- `docker login nvcr.io`
- `docker pull nvcr.io/nim/nvidia/cosmos3-reasoner:latest`
- `docker run ... --gpus all ... cosmos3-reasoner`

Preflight only: `./scripts/cosmos_nim_preflight.sh`.
