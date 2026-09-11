# Safety

Independent supervisor fails closed on: stale observation, missing required
sensors, NaN predictions, expired/invalid intents, speed/yaw limits, geofence,
blocked turn footprint, lost heartbeat, operator stop.

Dry-run adapter records intents and never opens serial/GPIO. `MavlinkRoverAdapter`
refuses `enabled=True` in this milestone.

TURN_180 is a one-shot trigger with clearance, timeout, wraparound, and
retrigger cooldown. Completing a pivot does **not** change coverage rows; a
lateral offset is a separate maneuver.

Software flags are not a physical e-stop. Arming requires separate owner
approval. Work/idle defaults (1800 s / 1200 s) are unconfirmed drafts.
