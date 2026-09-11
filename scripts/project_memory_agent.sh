#!/usr/bin/env bash
# Agent helpers for Project Memory v2.5.
#
#   ./scripts/project_memory_agent.sh ensure      # session start: redis + status
#   ./scripts/project_memory_agent.sh stop-gate   # Grok Stop hook: block if stale
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"
unset PROJECT_MEMORY_URL || true
unset BTC_USDT_ATOMIC_SWAP_PROJECT_MEMORY_URL || true

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ensure() {
  if [ -x "$ROOT/scripts/project_memory_redis.sh" ]; then
    "$ROOT/scripts/project_memory_redis.sh" start >/dev/null \
      || "$ROOT/scripts/project_memory_redis.sh" status >&2 || true
  fi
  python3 "$ROOT/project-memory.py" status >&2 || true
  python3 "$ROOT/project-memory.py" ledger-status >&2 || true
}

stop_gate() {
  python3 - "$ROOT" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
try:
    event = json.load(sys.stdin)
except json.JSONDecodeError:
    raise SystemExit(0)

if event.get("reason") != "end_turn":
    raise SystemExit(0)

def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=root,
        text=True,
        capture_output=True,
        timeout=25,
        check=False,
    )

status = run("python3", str(root / "project-memory.py"), "status")
if status.returncode == 0:
    raise SystemExit(0)

if status.returncode == 1:
    start = run("bash", str(root / "scripts/project_memory_redis.sh"), "start")
    status = run("python3", str(root / "project-memory.py"), "status")
    if status.returncode == 0:
        raise SystemExit(0)
    reason = (
        "Project Memory Redis is down or the cache is unreadable. "
        "Run ./scripts/project_memory_agent.sh ensure, then "
        "python3 project-memory.py index --incremental && "
        "python3 project-memory.py validate --deep, then finish the ledger "
        "update (session-close / consolidate) from AGENTS.md."
    )
else:
    reason = (
        "Project Memory cache is missing or stale. Before finishing, run "
        "python3 project-memory.py index --incremental && "
        "python3 project-memory.py validate --deep, then session-close and "
        "consolidate per AGENTS.md."
    )

json.dump({"decision": "block", "reason": reason}, sys.stdout)
sys.stdout.write("\n")
PY
}

case "${1:-}" in
  ensure) ensure ;;
  stop-gate) stop_gate ;;
  *)
    echo "usage: $0 ensure|stop-gate" >&2
    exit 2
    ;;
esac
