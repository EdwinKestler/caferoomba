# Architecture

Subject: coffee beans on a drying patio (redistribution/sweeping), not vacuuming
brewed grounds.

```
Training (offline):
  causal FPV clips + human labels [+ reviewed Cosmos auxiliaries]
      → small temporal policy

Deployment (onboard):
  recent FPV frames → student → typed intent → fail-closed supervisor
      → dry-run or (later) autopilot
```

Cosmos is an **offline teacher**. The exported student does not call Cosmos,
cloud APIs, or future frames.

Body-frame yaw is **left-positive**. ArduPilot Rover/NED yaw is opposite;
`to_mavlink_yaw_rate` negates the rate. Hardware adapters are disabled by
default.

Legacy GPIO rover code under `rover/` is preserved and is not imported by
`src/caferoomba`.
