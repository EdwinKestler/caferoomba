# Status and evidence

**Reviewed public baseline:** `eb9a2a427098b8f973d50b09906a9c75cb87a4a8` (2026-09-11).

**Documentation review:** 2026-09-12 UTC. This update publishes a website and documentation only. The Orin shadow integration was subsequently merged into main at `28c5ac1`; the media/experiment update starts from `c056adc`. The older baseline columns below are retained as historical comparisons, not a description of an unmerged current branch.

## Capability matrix

| Capability | Public baseline | Local work / remaining gate |
|---|---|---|
| CPU clips → train → ONNX → dry-run | Implemented and tested on synthetic fixtures | Does not measure field performance |
| Historical physical rover | Legacy source and owner media | Historical imagery is not validation of the newer policy |
| Small temporal student | Human action and turn-onset targets | Full-dataset trainer and held-out evaluation required |
| Cosmos teacher | Mock implementation; live function refuses execution | Authorized backend, reviewed annotations, and training integration required |
| Google Cloud Storage | Prior project records describe private media storage | Bucket not independently reinspected during this publication |
| Colab Enterprise training | Planned | Executed notebook/job, dataset hash, model artifact and report required |
| Companion FSM / camera buffer | Public dry-run skeleton | Local refactor adds stricter validation and shadow-mode composition |
| KML/KMZ geofence | Public placeholder | Local parser/projection/path checks; regression and hardware validation pending |
| Cube USB inspection | Public receive-only capture script | Local passive-serial and MAVSDK observation adapters need integration verification |
| RealSense / CSI | Public RealSense inspection and CSI stub | Local acquisition changes are not hardware-tested in the prior integration session |
| ONNX on Orin / TensorRT | Planned | Target environment and latency/parity evidence required |
| Sweeping, next-pass offset, return, docking | Intended mission | Complete closed-loop implementation and supervised trials required |

## Execution evidence

- Public CPU CI: [run 34632508366](https://github.com/EdwinKestler/caferoomba/actions/runs/34632508366), source revision above; installation and test job succeeded.
- Local pre-edit baseline: **26 tests passed** in `.venv-dev`, recorded in the prior implementation session.
- Local integration subset: **13 tests passed** in `test_geofence_integration.py` and `test_runtime_integrity.py` in `.venv`, before later edits.
- The full post-edit runtime regression, real-camera/Cube execution, Orin CSI execution, and cloud inference were **not completed** in that session.

These counts describe different source states and test sets. They are **not additive**, not test coverage percentages, and not navigation accuracy.

## Evidence vocabulary

`owner-reported` describes supplied hardware/use-case information. `implemented` means code is present at a named revision. `tested-offline` means an executed software test with a named environment. `tested-cloud` must name the actual cloud operation. `tested-on-device` must name the device and procedure. `planned` is not an implemented capability.

Synthetic examples must retain `is_synthetic=true`; mock annotations must retain `is_mock=true`. A successful upload, a configured API key, a diagram, and a model-shaped response are not proof of inference or learning.

## Sources of truth

Public code at the pinned revision; the CI run linked above; `docs/LOCAL_INTEGRATION_STATUS.md`; `docs/evidence/manifest.json` (historical record); and `docs/evidence/publication.json` (publication-level summary). Preserve historical records rather than changing their timestamps or reclassifying their runs.

## Media and experiment update

Two web-encoded dataset previews and two conceptual flow illustrations explain the proposed cloud-to-edge experiment. Public media is not a new hardware trial. The site now describes locally authored notebooks and the intended Colab Enterprise compute advantage; it does not claim a completed Colab/Cosmos run. The FPV-designated sample requires viewpoint and origin validation. See [This Experiment](EXPERIMENT.md) and [Media](MEDIA.md).
