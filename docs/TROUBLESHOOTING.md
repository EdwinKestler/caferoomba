# Troubleshooting

| Symptom | Inspect | Safe next action |
|---|---|---|
| Import works in one shell only | `sys.executable`, `.venv` vs `.venv-dev`, editable installation | Use the intended interpreter explicitly; do not install globally |
| All policy results are STOP | Configured ONNX path, current policy backend, shape/modality contract | Distinguish constant STOP fallback from model inference |
| Old CLI says `armed: false` or `ok: true` | Per-cycle logs and actual Cube telemetry | Treat old summary as insufficient; complete CLI refactor before hardware claims |
| Geofence rejects every point | Public placeholder vs local implementation; selected region; GPS freshness | Do not disable a required fence to make a test pass |
| KML path is inside but motion path exits | Polygon concavity, exclusions, footprint and projection | Validate the whole swept path in metric coordinates |
| Serial permission denied | Configured device and group/udev permissions | Have the operator approve any system-level permission change |
| Serial device busy | Existing GCS, capture tool or MAVSDK server | Stop only the explicitly owned process; never kill unrelated tools |
| RealSense produces IR instead of RGB | Actual USB mode, profile and camera backend | IR is diagnostic unless a separately validated model supports it |
| CSI does not open on workstation | Architecture and Jetson native stack | Test IMX219 on the Orin; do not fake a successful device check |
| Old/frozen images appear fresh | Capture/receipt clock domain, buffered frames, dispatch timestamp | Fault and diagnose timestamp mapping; do not reset timestamps to hide age |
| Turn never completes | Heading freshness, clearance, offset/alignment confirmation | Remain stopped; do not shorten the gate into an automatic success |
| Cosmos credentials exist but calls fail | `annotate_live()` is deliberately unimplemented | Implement and test the backend under explicit authorization |
| Training score looks excellent | Synthetic fixtures, repeated first batch, split leakage | Do not publish performance; fix dataset iteration and held-out evaluation |

Record the full command, source revision and redacted error. Do not paste keys, precise locations or private observations into public issues. [Security](../SECURITY.md).
