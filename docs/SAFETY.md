# Safety boundary

**This repository is not a certified robot safety system. Current public and local publication states do not authorize autonomous motion.** Hardware protection, physical emergency stop, operator procedures, firmware failsafes and supervised testing are required separately.

## Invariants

- The Cube/ArduPilot owns actuator outputs; the Jetson never directly drives traction or steering GPIO.
- No automatic arming, mode changes, firmware/parameter writes, raw PWM or RC overrides in the initial integration.
- Only one motion controller owns the vehicle link. Observe-only and passive capture must not be confused with drive authority.
- Missing required observations, unknown clearance, invalid geometry, non-finite predictions, stale telemetry and expired intents inhibit motion.
- Real-camera local integration remains HOLD with shadow predictions. The public dry-run demo is not hardware validation.

## Observation and command timing

Measure observation age at dispatch, after inference: `dispatch_time - capture_time`. Distinguish capture, receipt and inference-completion times. Do not silently clamp an invalid clock relationship into freshness. A stalled inference loop cannot supervise its own stall reliably; an independently expiring command/watchdog mechanism is required before enabling drive.

Confidence from a model is not a safety certificate. A valid model tensor does not establish obstacle clearance or remaining braking distance.

## Geofence and turns

KML uses longitude/latitude order. Distance buffers belong in a local metric frame. Validate robot footprint and complete proposed paths, not just current center and endpoints. Combine companion checks with independently configured Cube-side fences.

A forward depth image is not all-around clearance. Never treat missing depth, infrared substitution, unobserved rear space or a completed heading reversal as proof that the next pass is safe.

## Release gates

1. Offline tests and deterministic replay, including failure injection.
2. Real-camera and Cube telemetry observation with no commands sent.
3. Rover software-in-the-loop validation for command semantics and failures.
4. Target Orin inference/latency/clock validation.
5. Explicitly approved supervised physical trials with appropriate mechanical controls and an independent stop.

No gate may be inferred from a lower gate's success. The current local full post-edit regression and hardware tests remain pending as recorded in [Status](STATUS.md).

## Legacy warning

`docs/legacy code/rover_gpt.py` contains automatic arming, servo construction and blocking legacy execution. Do not import or execute it as a modern runtime bring-up shortcut.

References: [ArduPilot geofencing](https://ardupilot.org/rover/docs/common-geofencing-landing-page.html) and [Rover GUIDED commands](https://ardupilot.org/dev/docs/mavlink-rover-commands.html).
