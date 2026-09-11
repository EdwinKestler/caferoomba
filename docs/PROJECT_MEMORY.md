# Project Memory (CafeRoomba)

This repository uses portable Project Memory **v2.5.0** (version 25).
Agents and coding assistants **must** use it on every run. Humans may ignore
it.

Copied bundle layout:

```text
project-memory.py
project_memory/
.project-memory.json
```

Local ignored state lives under `.caferoomba/project-memory/`:

- owner-only Redis Unix socket and disposable v3 discovery dump
- durable SQLite ledger `memory-v25.sqlite3`

The committed project UUID in `.project-memory.json` isolates this cache from
other checkouts. Do not reuse another project's UUID or Redis URL. The generic
`PROJECT_MEMORY_URL` is ignored; only `CAFEROOMBA_PROJECT_MEMORY_URL` may
override the local socket.

## Agent protocol (required)

Run every command from the repository root. Put `~/.local/bin` on `PATH` if
`redis-server` is installed there. Do not store secrets in queries, payloads,
task names, or evidence locators.

### 1. Start of every run

```bash
./scripts/project_memory_agent.sh ensure
python3 project-memory.py status
# if status exits 2 (missing/stale):
python3 project-memory.py index --incremental
python3 project-memory.py validate --deep
python3 project-memory.py ledger-status
python3 project-memory.py recall "CURRENT TASK" --limit 10
python3 project-memory.py search "FOCUSED QUERY" --limit 5
python3 project-memory.py session-start --task "SHORT TASK NAME"
```

Save the 32-character `session_id`. Cache hits are discovery candidates: open
the current file before relying on them. If Redis is down, continue from files
and disclose `cache_consulted: false`. Still write the SQLite ledger.

### 2. During the run

- Search or recall before reusing a prior decision, invariant, or failure.
- After changing any file matched by `.project-memory.json`, run
  `python3 project-memory.py index --incremental`.
- Record durable facts when they happen:

```bash
python3 project-memory.py remember \
  --session SESSION_ID \
  --kind decision \
  --subject "area:topic" \
  --payload '{"decision":"short typed fact"}' \
  --retention durable \
  --evidence path/to/file.ext:START-END
```

Allowed kinds: `task`, `decision`, `failure`, `outcome`, `fact`, `evidence`,
`correction`, `revocation`. Default retention is `session`; only `durable`
promotes or exports.

### 3. End of every run

Do this before the final reply, even for small edits or Q&A that produced a
decision:

```bash
python3 project-memory.py index --incremental   # if admitted files changed
python3 project-memory.py remember ...            # remaining durable notes
python3 project-memory.py session-close SESSION_ID \
  --outcome "one-line outcome" \
  --evidence path/to/file.ext:START-END
python3 project-memory.py consolidate SESSION_ID
python3 project-memory.py status
python3 project-memory.py ledger-status
```

Report `cache_consulted`, freshness, and whether the ledger accepted the
session. Memory freshness does not prove tests, Git, or hardware.

Never use `FLUSHDB`, `FLUSHALL`, another project's Redis URL, or this
repository's raw Redis keys.

Grok also runs `./scripts/project_memory_agent.sh ensure` on session start
and blocks a turn from ending while the discovery cache is stale. Project
hooks need folder trust (`/hooks-trust` or `grok --trust`). Other assistants
rely on `AGENTS.md`, `CLAUDE.md`, and the project-memory skill.

## Initialize or rebuild (operators)

```bash
./scripts/project_memory_redis.sh start
python3 project-memory.py --version
python3 project-memory.py ledger-init
python3 project-memory.py index --incremental
python3 project-memory.py validate --deep
python3 project-memory.py evaluate --limit 5
python3 project-memory.py ledger-status
```

`cache_mode` is `on` (v3 authoritative). This is a new cache, not a v2-to-v3
migration, so `migration-shadow` is not required.

The discovery index covers admitted UTF-8 sources in `.project-memory.json`
(rover code, docs, memory bundle, templates). Videos, camera photos, Office
binaries, and the frozen evaluation fixture stay out.

Operator details: `docs/PROJECT_MEMORY_V25_RUNBOOK.md`.
Design: `docs/PROJECT_MEMORY_V25_DESIGN.md`.
Bundle reference: `project_memory/README.md`.
