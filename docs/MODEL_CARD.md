# Model card (student)

| Item | CPU milestone |
|---|---|
| Backbone | `tiny` Conv2d+Conv1d (fixture). `mobilenet_v3_small` is available but not required for smoke. |
| Inputs | `B,T,C,H,W` past/current frames only. Default smoke: T=8, H=W=64 |
| Outputs | LEFT/STRAIGHT/RIGHT/STOP logits; TURN_180 logit |
| Primary loss | cross-entropy on **human** action + BCE on human turn onset |
| Teacher | optional auxiliary; mock never counts as Cosmos |
| Export | static ONNX, CPU onnxruntime, class order `LEFT,STRAIGHT,RIGHT,STOP` |
| Device for smoke | CPU (`torch==2.14.0+cpu`) |

Fixture accuracy is not patio coverage, docking, or agricultural benefit.
