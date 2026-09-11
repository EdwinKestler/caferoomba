---
name: project-memory
description: Default for every CafeRoomba session. Load at start of every run, search/recall before coding, reindex after admitted-file changes, and update the durable ledger before finishing. Do not skip.
---

# Project Memory is the default

Follow `AGENTS.md` and `docs/PROJECT_MEMORY.md`. This skill does not replace
them. Use it on every run, including small edits.

Run from the repository root.

## Start

```bash
./scripts/project_memory_agent.sh ensure
python3 project-memory.py status
python3 project-memory.py index --incremental   # when status exits 2
python3 project-memory.py validate --deep       # after a rebuild
python3 project-memory.py ledger-status
python3 project-memory.py recall "TASK" --limit 10
python3 project-memory.py search "FOCUSED QUERY" --limit 5
python3 project-memory.py session-start --task "SHORT TASK NAME"
```

Keep the `session_id`. Cache hits are discovery candidates; open current
repository files before relying on them.

## During

Reindex after changing files listed in `.project-memory.json`. Record durable
work with evidence locators:

```bash
python3 project-memory.py remember \
  --session SESSION_ID \
  --kind decision \
  --subject "area:topic" \
  --payload '{"decision":"short typed fact"}' \
  --retention durable \
  --evidence path/to/file.ext:START-END
```

## End (required)

```bash
python3 project-memory.py index --incremental
python3 project-memory.py session-close SESSION_ID \
  --outcome "one-line outcome" \
  --evidence path/to/file.ext:START-END
python3 project-memory.py consolidate SESSION_ID
python3 project-memory.py status
python3 project-memory.py ledger-status
```

If Redis is down, continue from files and disclose `cache_consulted: false`;
still write SQLite. Never `FLUSHDB`/`FLUSHALL`, never another project's URL,
never secrets in payloads. Memory does not authorize Git, network, hardware,
or destructive writes.
