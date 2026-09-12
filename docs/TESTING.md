# Testing and evidence

## Existing evidence

The public baseline CI succeeded at `eb9a2a427098b8f973d50b09906a9c75cb87a4a8`. The prior local implementation session recorded 26 pre-edit tests passing in `.venv-dev` and 13 new focused integration tests passing in `.venv` before subsequent edits. The final full post-edit regression and physical sensor tests were not completed. [Evidence matrix](STATUS.md).

## Test environments

```bash
# Published CPU suite: requires CPU training/export dependencies
.venv-dev/bin/python -m pytest tests -q

# Local integration only: these files are not in the public baseline
.venv/bin/python -m pytest tests/test_geofence_integration.py tests/test_runtime_integrity.py -q
```

Do not expect a minimal runtime `.venv` without PyTorch to run the full training suite. Do not install GPU/runtime dependencies merely to build the website.

## Required regression coverage

| Layer | Required failure cases |
|---|---|
| Dataset | Future input frames, overlapping runs across splits, empty train split, invalid labels |
| Inference | Wrong shapes/classes, NaN/Inf, missing model, modality changes, mismatched temporal spacing |
| Geofence | KML coordinate order, holes, concavity, invalid/ambiguous KMZ, missing maps, stale position |
| Timing | Slow inference, capture stalls, duplicate/out-of-order frames, stale GPS/heading/heartbeat |
| Mission | Illegal transitions, manual takeover, repeated turn triggers, missing alignment, timeout |
| Serial | Port ownership, disconnect, wrong system identity, proof of no actuation in observe mode |
| Recording | Full queue, disk errors, partial runs, timestamps and dropped-record reporting |

## Hardware gating

Hardware tests require explicit selection and a documented setup. The first device-level run should use actual camera/telemetry inputs with **zero motion commands**. Simulation comes before supervised actuation. Record the precise host, source revision and model hash for each result.

## Website checks

The site builder only reads an allowlisted document set and curated media. `scripts/check_site.py` checks generated internal links, assets, fragment targets and required pages. `tests/test_site.py` validates the site in isolation. Run these in the website environment; they do not import or execute robot code.

Website tests are publication-quality checks, not robot regression evidence.
