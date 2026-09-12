# Private media and Google Cloud Storage

Repository records describe owner media in **`gs://caferoomba`**, with the established prefix **`media/`**. That storage record is distinct from live inference or model training. The bucket and its access controls were not independently re-audited during the website publication.

## Existing mapping

| Local ignored input | Established prefix |
|---|---|
| `docs/videos/` | `media/docs/videos/` |
| `docs/pictures/` | `media/docs/pictures/` |
| `docs/docs/` | `media/docs/docs/` |
| `docs/DesginSTL/` | `media/docs/DesginSTL/` |
| `data/raw/` | `media/data/raw/` |

The historical inventory remains in `docs/evidence/gcs_media_inventory.json`. Preserve it as a dated record, not a current live listing.

## Proposed versioning

Use immutable run/model identifiers for `media/data/raw/runs/<run_id>/`, `datasets/<version>/`, `models/<version>/`, `maps/<version>/` and `reports/<run_id>/`. Upload complete local artifacts through a separate queue, with hashes, retry limits and generation preconditions. Do not overwrite an active model or map during a mission.

Raw camera frames, recordings, precise coordinates, faces, serial identifiers and credentials stay private by default. Never synchronize `.env`, virtual environments, Project Memory ledgers or the whole repository indiscriminately.

## Website separation

The public site contains only curated, metadata-stripped derivative images copied to `site/assets/`. It does not read the private bucket, embed signed URLs, change bucket ACLs, or expose raw datasets. Public media is enumerated in [MEDIA.md](MEDIA.md).

Cloud credentials belong in an appropriate local authentication or secret-management mechanism, not committed files. Use the existing environment variable names without displaying their values. Review `scripts/gcs_sync_ignored_media.sh` before any operator-authorized upload.

Reference: [Google Cloud Storage upload example and generation preconditions](https://cloud.google.com/storage/docs/samples/storage-upload-file).
