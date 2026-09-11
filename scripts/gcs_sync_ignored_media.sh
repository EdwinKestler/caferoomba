#!/usr/bin/env bash
# Upload gitignored large media to the CafeRoomba GCS bucket.
# Reads project/bucket from .env. Never prints secret values.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "missing .env" >&2
  exit 1
fi

eval "$(python3 - <<'PY'
from pathlib import Path
vals = {}
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, v = s.split("=", 1)
    vals[k] = v.strip().strip("'").strip('"')
bucket = vals.get("CAFEROOMBA_GCS_BUCKET", "")
project = vals.get("GOOGLE_CLOUD_PROJECT", "")
if bucket and not bucket.startswith("gs://"):
    bucket = "gs://" + bucket
print(f"BUCKET={bucket!r}")
print(f"PROJECT={project!r}")
PY
)"

if [ -z "${BUCKET:-}" ]; then
  echo "CAFEROOMBA_GCS_BUCKET is empty" >&2
  exit 1
fi
PREFIX="${BUCKET%/}/media"

echo "project=${PROJECT:-unset}"
echo "prefix=$PREFIX"
echo "this script does not make objects public"

sync_dir() {
  local src="$1" dest="$2"
  if [ ! -d "$src" ]; then
    echo "skip missing $src"
    return 0
  fi
  echo "rsync $src -> $dest"
  if [ -n "${PROJECT:-}" ]; then
    gcloud storage rsync --recursive "$src" "$dest" --project "$PROJECT"
  else
    gcloud storage rsync --recursive "$src" "$dest"
  fi
}

sync_dir docs/videos "$PREFIX/docs/videos"
sync_dir docs/pictures "$PREFIX/docs/pictures"
sync_dir docs/docs "$PREFIX/docs/docs"
sync_dir docs/DesginSTL "$PREFIX/docs/DesginSTL"
sync_dir data/raw "$PREFIX/data/raw"

echo "done"
