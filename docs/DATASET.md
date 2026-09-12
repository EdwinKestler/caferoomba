# Demonstration dataset

## Separate footage from demonstrations

Historical external-camera footage documents the physical prototype. It is not automatically an FPV training sample. A usable imitation-learning run pairs the robot's view with synchronized operator commands and measured robot state.

The public schema is `caferoomba.record.v1`. Preserve `viewpoint` (`FPV`, `EXTERNAL`, `SYNTHETIC`), `run_id`, label provenance and `is_synthetic`. Missing telemetry is omitted, not invented as zero.

## Minimal run structure

```text
data/raw/fpv/<run_id>/
  run.json            # metadata, device/calibration identity, rights, hashes
  video.*             # original observations, private
  telemetry.jsonl     # capture/receipt times and measured state
  controls.jsonl      # actual human commands and their timestamps
  labels.jsonl        # reviewed action and turn-onset labels
```

Original videos, faces, deployment coordinates, serial identifiers and raw logs are private by default. Version manifests and redacted evaluation records can be shared without making the bucket public.

## Causal input contract

For a decision at time t, every input frame must be observed at or before t. Preserve original timestamps and report clock mappings, tolerances and synchronization errors. Do not derive a turn-onset label from future frames and then leak those frames into the policy input.

Distinguish commanded steering from observed yaw. Slippage, latency and operator intervention can make them differ. Label LEFT/STRAIGHT/RIGHT/STOP separately from the event that initiates a 180-degree maneuver.

## Splits and evaluation

Split by complete runs, sessions or physical settings before extracting overlapping clips. Do not randomly split near-identical adjacent frames across training and test sets. Empty/missing training splits must raise an error, not fall back to all examples. The public smoke trainer currently has that fallback and is not ready for held-out scientific evaluation.

Report class balance, missed/false turn events, intervention frequency, observation latency, and eventually coverage and return/docking outcomes. Do not turn synthetic classification accuracy into an agricultural-impact claim.

## Teacher annotations

Cosmos annotations are suggestions with model/prompt/input hashes, uncertainty, abstention and reviewer state. Human controls remain primary supervision. In the public code, mock annotations are generated but not used by `train_steps`; live teacher and annotation-to-loss wiring remain pending.

[Model card](MODEL_CARD.md) · [Cloud storage](GCS_MEDIA.md) · [Testing](TESTING.md).
