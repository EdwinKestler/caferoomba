# Real FPV Colab training

The baseline trains from reviewed human labels. NVIDIA/Cosmos access is optional
and unused by this path; no key is read and no teacher requests occur. Raw video
is not a label. Do not relabel fixture results as real-data learning.

## Runtime setup

Use notebooks 01, 02, then 03, each from the same published implementation
revision. Set `CAFEROOMBA_REVISION` to its full commit SHA before running the
bootstrap cell. The cell clones only into a new directory and rejects a dirty
or different existing checkout. Until these changes are committed and published,
the notebooks cannot fetch them from GitHub. For local development use the
Python APIs directly from this checkout.

Python 3.11+ and ffmpeg/ffprobe are required. Notebook setup installs `.[cpu,dev]`
with the active kernel interpreter, preserving already compatible Torch packages.
Despite the historical extra name `cpu`, it does not replace a compatible
CUDA-enabled Torch with CPU-only wheels. CPU is the training default; choose
`CAFEROOMBA_TRAIN_DEVICE=cuda` only on an already selected GPU runtime. No code
creates billable cloud resources. Restart a previously used kernel after changing
installed package versions. Package versions are recorded with training provenance;
the repository revision is pinned but dependency resolution is not a lockfile.

Mount persistent storage and set `CAFEROOMBA_WORKSPACE` to an existing directory.
Use the same workspace across notebooks. On consumer Colab, explicit Drive
mounting is one option; Enterprise users should use their own persistent mount or
copy complete versioned artifacts to/from their private GCS storage. Ordinary
`/content` and `/tmp` disappear when a runtime is deleted. The code cannot prove
that a user-selected directory is durable. Atomic replace/locking behavior also
depends on the mounted filesystem; keep backups and use one writer per run.

```text
workspace/
  media/                     original videos, private
  labels.reviewed.jsonl     reviewed combined labels
  dataset-v1/               immutable prepared dataset and manifest
  run-v1/                   checkpoints, metrics, export reports
```

## Label and timestamp contract

Each reviewed row must identify its run, original video path relative to `media/`,
SHA-256, decision timestamp in the video's presentation-timestamp domain, human
action, explicit turn-onset flag, reviewer and FPV viewpoint. `status` must be
`reviewed`, `label_source` must be `human`, `is_synthetic` must be false. Unknown
labels, external viewpoints and unreviewed drafts are rejected, not silently
converted. At least three independent run groups are required; source-video
hashes and session identities must not cross splits.

Example row (replace placeholders with verified values, not invented labels):

```json
{"schema_version":"caferoomba.record.v1","run_id":"run-001","video_path":"run-001/video.mp4","video_sha256":"FULL_VERIFIED_SHA256","decision_timestamp_ms":2000,"viewpoint":"FPV","action":"STOP","turn180_onset":false,"label_source":"human","reviewer":"reviewer-id","status":"reviewed","is_synthetic":false}
```

Use STOP only when that is the actual reviewed action. Drafts made by
`scripts/draft_fpv_jsonl.py` remain unusable until reviewed; combine reviewed rows
and make their video paths relative to the common media root. Retain meaningful
`session_id` values for related runs. Label time is original video PTS, not the
zero-based timeline of an independently trimmed shard. Operator timestamps, if
provided, must already be mapped into that domain; missing operator timestamps
do not establish synchronization accuracy.

Preparation selects the latest decoded frame at or before each requested sample
time using actual PTS, rejects excessive age, and never substitutes future frames.
Prepared frame hashes and dataset identity are verified on load. Choose a new
dataset directory after any label or source change; do not overwrite a published
dataset. Teacher annotations are not needed for this human-only baseline and
are not wired into its loss.

## Training and handoff

Notebook 02 defaults to 10 total epochs, batches of 8 and CPU. Override
`CAFEROOMBA_EPOCHS`, `CAFEROOMBA_BATCH_SIZE`, `CAFEROOMBA_TRAIN_DEVICE` as needed.
All training samples are visited per epoch; images are loaded per batch.
Validation alone selects `best.pt`; test images are not used for model selection.
`last.pt` stores optimizer/RNG state for resume. Set `CAFEROOMBA_RESUME` to that
checkpoint and increase the total target epochs. Resume rejects incompatible
dataset/configuration. Do not load untrusted `.pt` uploads: Torch checkpoints
are only for artifacts you produced and trust.

Notebook 03 evaluates the selected checkpoint on test once per saved artifact
identity, persists the result and exports that same model. Re-running reuses
saved test metrics. It is a convenience guard, not a secure sealed-test service;
new runs can reuse the test set, which must be disclosed in experimental claims.
Export compares PyTorch/ONNX numerical outputs on up to 16 validation clips and
fails on mismatch. It records hashes, RGB preprocessing, temporal spacing and
class order. This is not a robot safety or generalization gate.

Keep the full dataset and run folder together when moving runtimes. The report
uses relative checkpoint filenames. `student.onnx` requires no teacher or cloud
at inference time. Run shadow replay and verify latency/operators on the actual
Orin separately; do not treat desktop or Colab execution as target acceptance.

## Validation boundary

Automated tests use synthetic frames and generated test videos to check software
contracts, leakage rejection, resume, notebook handoffs and export. They do not
establish real-patio accuracy. A real-data baseline still requires the owner's
reviewed demonstration dataset and execution in the selected Colab runtime.

Local verification on 2026-09-12: 110 tests passed on Python 3.11.15, including
all three notebooks' stage code with generated videos, selected-frame pixel
agreement, moved dataset/run handoff, deterministic CPU resume and representative
ONNX export. Bootstrap cells were syntax/structure checked, not executed against
a fresh Colab runtime. Scoped Ruff, byte compilation, diff checks and the installed
development dependency consistency check passed. GPU behavior remains unverified;
the CUDA RNG restoration regression uses a mock, not a GPU. No NVIDIA key was
read, no API call was made and no billable runtime was started for this work.
