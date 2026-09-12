# Local Orin companion integration — 2026-09-11

Working machine: `andorxps` (x86_64), not the Jetson.
Repository: `/home/kestl/github/caferoomba`.
Branch: `feat/orin-shadow-integration`.
Starting commit: `eb9a2a427098b8f973d50b09906a9c75cb87a4a8`.
Changes are local and uncommitted; nothing was pushed.

## Verification actually completed

- Before editing: all 26 existing tests passed in `.venv-dev`.
- After the integration edits: all 13 tests in `test_geofence_integration.py`
  and `test_runtime_integrity.py` passed in the runtime `.venv`.
- Python in `.venv` is 3.11.15. Native system packages were not replaced.
- MAVSDK 3.17.2 imported successfully in `.venv`; its lifecycle API was inspected.
- The subsequent terminal requests were blocked by the execution guard,
  including the hardware inventory and full runtime test request.
- Therefore no USB camera/Cube test, Orin/CSI test, or full post-edit suite
  is claimed. File editing remained available after execution was blocked.

## Safety boundary

All vehicle backends are non-actuating. The serial-passive backend parses
received bytes only. MAVSDK is observation-only but may send protocol traffic.
Real-camera runtime profiles remain HOLD while calculating shadow predictions.
The software does not arm, change vehicle mode, write PWM, or send motion.
