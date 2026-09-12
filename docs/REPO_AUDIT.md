# Repository audit

Evidence states used below: `user_reported`, `implemented`, `tested_offline`,
`tested_cloud`, `tested_on_device`, `planned`, `blocked`.

| Field | Value |
|---|---|
| Inspected commit | `63cedd05c7b8fec80ff9ad05668196df20443c7a` (`main` at start) |
| Working branch | `feature/cpu-offline-pipeline` |
| Host | x86_64 Linux, Python 3.11.15, Grok 1.0.25, not a Jetson |
| GPU on host | NVIDIA GeForce RTX 3090 Ti (driver 580.173.02) — **development host**, not the robot |
| Extra local files at start | `docs/CafeRoomba_Grok_Implementation_Prompt.md`, `docs/orangeCubeBoard/` |

## Historical rover (preserved)

| Path | Finding | State |
|---|---|---|
| `rover/robot.py:54` | `("rigth", "x")` typo in FSM table | `implemented` (pre-existing) |
| `rover/robot.py:225-237` | `turn_degree_left()` calls `right()`; `turn_degree_rigth()` calls `left()` — likely differential-drive convention, not proven wrong without wiring evidence | `user_reported` |
| `rover/robot.py:219-223` | `advance_meters` is open-loop sleep, not closed-loop heading | `tested_offline` (code read) |
| `rover/cofee_rover.py:15-34` | `getch()` already applies transitions; outer loop applies them again — duplicate actuation risk | `user_reported` |
| `rover/robot.py:10-15` | `Robot()` constructs `Servo`/`pigpio` — tests must not instantiate | `implemented` (new package avoids this) |
| `rover/requirements.txt:13` | `pkg_resources==0.0.0` plus GPIO/Flask/virtualenv pins | `blocked` as modern env; not installed |

## New CPU pipeline

| Item | State |
|---|---|
| `src/caferoomba` causal clips, mock teacher, tiny student, ONNX, dry-run | `implemented` / `tested_offline` after pytest |
| Live Cosmos (`nvidia/cosmos3-nano-reasoner`) | `blocked` (no `NVIDIA_API_KEY` / teacher URL; spending = 0) |
| Colab Enterprise training | APIs, billing, IAM, and runtime templates enabled; no job executed |
| Jetson TensorRT / onboard loop | `blocked` (host is not Jetson) |
| Cube Orange MAVLink send | `blocked` (adapter disabled; no arming) |
| Real FPV policy dataset | `blocked` (no authorized FPV files in checkout) |

Source existence is not physical execution. Videos under `docs/videos/` are gitignored and were not ingested.
