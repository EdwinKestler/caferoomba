# Raw FPV demonstrations

Drop owner FPV runs here. This is **not** `src/caferoomba/data/` (Python ingest
code) and not `docs/videos/` (legacy unlabelled phone footage).

```text
data/raw/fpv/<run_id>/video.mp4
data/raw/fpv/<run_id>/labels.json
```

`<run_id>` should be a whole session (one patio/day), for example
`2026-09-11-patio-a`.

Label `viewpoint` as `FPV`. Put third-person cameras under
`data/raw/external/` instead — those cannot enter the FPV policy set.

Videos and labels stay local (gitignored except this README). Extracted frames
go to `data/generated/`.
