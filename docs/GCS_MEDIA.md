# Gitignored media on Google Cloud Storage

Private bucket: `gs://caferoomba` (project `flatbox-serverless-demos`,
location `US`, uniform bucket-level access). Objects are **not** public.

Local `.env` holds `NVIDIA_API_KEY`, `X_AI_API_KEY` / `XAI_API_KEY`, and
Google Cloud project/bucket names. `.env` is gitignored. Copy
`.env.example` and never commit filled values.

Upload mapping (local → GCS):

| Local (gitignored) | GCS prefix |
|---|---|
| `docs/videos/` | `gs://caferoomba/media/docs/videos/` |
| `docs/pictures/` | `gs://caferoomba/media/docs/pictures/` |
| `docs/docs/` | `gs://caferoomba/media/docs/docs/` |
| `docs/DesginSTL/` | `gs://caferoomba/media/docs/DesginSTL/` |
| `data/raw/` | `gs://caferoomba/media/data/raw/` |

Re-run:

```bash
chmod 600 .env
./scripts/gcs_sync_ignored_media.sh
```

Inventory after the 2026-09-11 sync is in `docs/evidence/gcs_media_inventory.json`.
This upload is **storage of owner media**, not Cosmos inference, Colab training,
or Jetson evidence.
