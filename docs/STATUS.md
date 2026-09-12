# Status and evidence

**Published software revision:** `cd0bb2d485831c6b040f933d7ee87ca22b2569f8`
(2026-09-12), including portable-runtime revision
`db7caec2f0a2d3ae95a692e65c7dedfddc85933c`.

**Documentation review:** 2026-09-12 UTC. “Closed” below is scoped to software
implementation and named offline/CI checks. It does not mean trained on the
owner's real data, deployed to an Orin, or proven on a moving rover. Later local
documentation and preflight changes remain unpublished until committed, pushed
and accepted by their own CI/Pages runs.

## Capability matrix

| Capability | Evidence state | Current boundary / remaining gate |
|---|---|---|
| Local software integration (roadmap Stage 1) | `implemented` / `tested_offline`; closed at `cd0bb2d` | The full CPU CI suite and the Ubuntu 22.04/Python 3.11 runtime-only job succeeded. This is not hardware acceptance |
| Real FPV preparation and full-data learning implementation (Stage 3) | `implemented` / `tested_offline`; implementation closed | Reviewed-label validation, PTS-aware extraction, disjoint splits, minibatches, resume, validation selection, held-out evaluation and representative ONNX export are present. No owner real-data training has run |
| Portable companion runtime | `implemented` / `tested_offline` at `db7caec` and later `cd0bb2d` CI | Composition root, fail-closed FSM/supervisor, USB cameras, passive Cube observations and configurable ONNX providers are covered; no physical commands are implemented |
| Passive USB hardware observation (part of Stage 2) | `tested_on_device` on the x86_64 development host only | RealSense, UVC and passive Cube telemetry were observed separately. Synchronized demonstration recording, calibration and timestamp mapping remain open |
| Cosmos teacher | Mock is `tested_offline`; live path is `blocked` | Requires an authorized live request/response record, reviewed annotations and an explicitly integrated learning objective |
| Colab Enterprise | Historical CPU smoke is `tested_cloud` | The current real-data notebooks were not run in Colab; no real-data/GPU training result exists |
| ONNX on Orin / TensorRT | `planned` | Requires native ARM64 dependency, provider parity, latency and representative-output evidence on the actual Orin |
| Navigation, physical commands and docking | `planned` | Requires command expiry/watchdog, Rover simulation, operator stop authority, calibrated sensors and supervised physical trials |

## Current execution evidence

- CPU CI [run 34710087792](https://github.com/EdwinKestler/caferoomba/actions/runs/34710087792)
  succeeded at `cd0bb2d`: the Ubuntu 22.04/Python 3.11 `portable-runtime`
  job and the Ubuntu 24.04 full test job both completed successfully.
- Website [run 34710087793](https://github.com/EdwinKestler/caferoomba/actions/runs/34710087793)
  built, checked and deployed the allowlisted site at `cd0bb2d`.
- The training implementation's named local verification at `cd0bb2d` was
  **110 tests passed** on Python 3.11.15, plus scoped Ruff, byte compilation,
  dependency consistency and diff checks. Generated videos and synthetic
  frames exercised the pipeline; no real dataset, GPU or Colab runtime was used.
- The portable-runtime review records x86_64 host-only camera/Cube observation
  artifacts and zero physical commands. See
  [Runtime portability review](RUNTIME_PORTABILITY_REVIEW.md).

These results are not additive test counts, coverage percentages, navigation
accuracy, data quality measurements or robot performance.

## Evidence vocabulary

Allowed states are `user_reported`, `implemented`, `tested_offline`,
`tested_cloud`, `tested_on_device`, `planned` and `blocked`.
`tested_on_device` must name the actual device and procedure; it does not imply
the target Orin when the named device is the x86_64 development host.

Synthetic examples must retain `is_synthetic=true`; mock annotations must retain
`is_mock=true`. A successful upload, configured API key, diagram, model-shaped
response, passing fixture, or registered inference provider is not proof of
real-data learning, live inference, accelerator execution or physical autonomy.

## Open acceptance work

The next evidence gates are the synchronized and calibrated demonstration
dataset; reviewed human labels; actual current-notebook execution in Colab;
optional authorized live Cosmos annotations; deterministic navigation replay and
Rover simulation; native Orin/TensorRT validation; and separately authorized
physical command, navigation, sweeping and docking trials. See the
[roadmap](PENDING_WORK.md).

## Historical publication snapshot

The earlier public baseline `eb9a2a427098b8f973d50b09906a9c75cb87a4a8`
and CI [run 34632508366](https://github.com/EdwinKestler/caferoomba/actions/runs/34632508366)
predated the merged portable runtime and full-data training implementation.
Prior notes recorded 26 pre-edit tests and a 13-test integration subset at
different source states. They remain historical evidence, not the current
acceptance result and not values to add together.

`docs/evidence/manifest.json` remains a historical record and
`docs/evidence/publication.json` remains a publication-scope summary; neither is
rewritten to imply later execution. Public preview media and conceptual diagrams
remain presentation material, not new hardware or autonomy trials.
