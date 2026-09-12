# Local Orin companion integration

Working machine: `andorxps` (x86_64), not the Jetson.
Repository: `/home/kestl/github/caferoomba`.

## Verification

- Ruff is clean on `src`, `tests`, and `scripts`.
- `pytest tests` in `.venv-dev` passes after installing the `geofence` extra
  (`lxml`, `shapely`, `pykml`).
- CPU CI installs `.[dev,geofence]`.
- Vehicle backends remain non-actuating. Software does not arm, change mode,
  write PWM, or send motion.

## Safety boundary

The serial-passive backend parses received bytes only. MAVSDK is
observation-only but may send protocol traffic. Real-camera runtime profiles
remain HOLD while calculating shadow predictions.
