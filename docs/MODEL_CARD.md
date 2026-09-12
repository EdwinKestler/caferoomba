# Student model card

## Intended use

Research and software integration for a camera-based coffee-patio navigation policy. The current fixture model is not validated for autonomous actuation.

| Property | Current public implementation |
|---|---|
| Family | Small temporal visual policy |
| Smoke backbone | `tiny` spatial/temporal convolution; optional MobileNet path in source |
| Input | Float image history shaped `B,T,C,H,W`; smoke configuration `1,8,3,64,64` |
| Class order | `LEFT, STRAIGHT, RIGHT, STOP` |
| Additional output | Turn-onset logit, not a complete turn trajectory |
| Targets | Human action cross-entropy plus human turn-onset binary cross-entropy |
| Export | Static-shape ONNX; public replay uses CPU ONNX Runtime |
| Teacher dependency onboard | None |
| Data evidence | Synthetic fixture; no published real-FPV-trained navigation artifact in this release |

## Critical limitations

The public smoke trainer reuses the first small batch. It falls back to all clips if the train split is empty; this must be removed before held-out evaluation. The current dataset loader does not consume Cosmos annotations. Thus this publication does not describe a Cosmos-distilled policy, Cosmos fine-tune, or Google Cloud-trained checkpoint.

A turn trigger does not select a safe pivot direction, verify clearance, establish an adjacent coverage path, or complete docking. Model softmax/turn scores are not physical safety signals.

## Deployment contract

Version each artifact with its source revision, dataset split hashes, preprocessing, RGB/modality expectations, temporal spacing, class order, input shape, output semantics, numeric precision and checksum. Compare PyTorch, ONNX, and any target TensorRT results on representative inputs—not only a zero tensor. Report measured target latency separately from model accuracy.

The local integration adds output/shape checks and model hashing, but remains a separately unmerged source state. Do not infer target compatibility from desktop import success.

## Required evaluation before a stronger claim

Real demonstration training with a fixed held-out set; teacher-versus-no-teacher ablation when annotations are implemented; per-class/event errors; timestamp/failure injection; then supervised target-device trials with independent safety controls.
