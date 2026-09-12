# Mission state machine

Use one authoritative mission FSM and one maneuver sub-FSM. State transitions should be deterministic; hardware I/O belongs in adapters, not transition-table callbacks.

## Public baseline

```text
OFF → PRECHECK → HOLD → SWEEP ⇄ TURN → RETURN → IDLE
                      └───────── FAULT / ESTOP ──────┘
```

The table is implemented in `src/caferoomba/app/fsm.py`. The public companion loop is a dry-run skeleton. The existence of a RETURN state does not mean homeward routing or docking is implemented.

## Local shadow integration

Real-camera profiles remain in **HOLD** while policy proposals and telemetry are observed. The fake-camera/dry-run example may advance its simulated mission. Local turn integration still requires clearance and an explicit next-pass alignment signal; it is not a motion-ready coverage planner. These local changes are separate from the public baseline.

## Intended mission

| State | Entry/exit contract |
|---|---|
| PRECHECK | Validate configuration, map, model contract, devices and observation quality within deadlines |
| HOLD | No autonomous motion; shadow inference allowed; explicit authority required to leave |
| SELECT_PATCH | Select a reachable, unserved patch inside the safe operating region |
| APPROACH_PATCH | Follow a verified path using local observations and vehicle state |
| SWEEP | Execute bounded, validated intents and account for real work time |
| TURN | Verify clearance, track heading reversal, move onto the next pass, verify alignment |
| RETURN_HOME | Follow a validated route under one controller's authority |
| DOCK_VERIFY | Confirm docking/contact; GPS proximity is insufficient |
| CHARGING / IDLE | Require charging/energy readiness before any wake timer can start another mission |
| FAULT | Inhibit motion until explicit recovery and fresh prechecks |
| ESTOP | Latched emergency stop; software reset cannot substitute for a physical stop system |

SELECT_PATCH, APPROACH_PATCH, DOCK_VERIFY and CHARGING are **planned** stages, not evidence of completed code.

## Turn sub-machine

```text
SWEEP → VERIFY_TURN_CLEARANCE → TURNING
      → ALIGN_ADVANCE_PASS → SWEEP
Any unsafe condition or deadline failure → STOP_FAULT
```

A 180-degree pivot reverses heading but normally retraces the same line. A feasible connector must establish the adjacent pass. For measured brush width W and chosen overlap fraction rho, proposed spacing is `W * (1 - rho)`; validate footprint and steering geometry before treating that as executable motion.

Required tests include illegal transitions, stale telemetry, inference delays, manual takeover, repeated triggers, heading wraparound, clearance loss, turn timeout, and absent next-pass alignment.
