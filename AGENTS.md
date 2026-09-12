# Repository agent instructions

This repository is **caferoomba**, an autonomous coffee-grounds sweeper rover.
Repository files are always the authoritative source of truth.

## Model routing policy

`GPTagentTree.png` defines this repository's model routing policy. The executable
defaults live in `.codex/config.toml` and `.codex/agents/*.toml`; operational
details are in `docs/MODEL_ROUTING.md`.

- Root orchestration, integration, and verification: `gpt-6-astra`, `medium`.
- Bounded code investigation: `explorer`, `gpt-5.6-luna`, `max`.
- Implementation and tests: `worker`, `gpt-5.6-sol`, `high`.
- Focused external documentation lookup: `researcher`, `gpt-5.6-luna`, `max`.
- Independent review only when needed: `reviewer`, `gpt-6-astra`, `xhigh`.

Delegate on demand when a bounded subtask benefits from delegation. Do not spawn
every role, delegate trivial work, or duplicate work already running. Assign
workers disjoint file ownership and explicit validation criteria. Root owns
integration and verification. Use independent review for material safety,
security, persistence, concurrency, or unresolved correctness risks; explain
the trigger. Child agents return findings to root without further delegation.

When tools expose model and reasoning overrides instead of named agents, pass
the exact pair above explicitly and give the child a self-contained task with
minimal context (not a full-history fork that forces model inheritance).
If an exact model/effort or named role is unavailable, report the limitation;
do not silently substitute another model or claim routing was applied.
Runtime instructions and explicit user overrides take precedence. Selecting
a model never grants additional sandbox, network, hardware, or spend authority.

## Project Memory is mandatory

Use Project Memory v2.5 on **every** run, including small edits, reviews, and
questions. Do not skip it as optional or "self-contained". Full protocol:
`docs/PROJECT_MEMORY.md`.

Run from the repository root (`export PATH="$HOME/.local/bin:$PATH"` if needed).

**Start of the run**

```bash
./scripts/project_memory_agent.sh ensure
python3 project-memory.py status
# exit 2 => python3 project-memory.py index --incremental && python3 project-memory.py validate --deep
python3 project-memory.py ledger-status
python3 project-memory.py recall "TASK" --limit 10
python3 project-memory.py search "FOCUSED QUERY" --limit 5
python3 project-memory.py session-start --task "SHORT TASK NAME"
```

**During**

- Treat cache hits as candidates; open the current file before relying on them.
- After changing files matched by `.project-memory.json`, `index --incremental`.
- `remember` durable decisions, failures, and outcomes with a source evidence
  locator (`path:start-end`) and `--retention durable`.

**End of every run (required before the final reply)**

```bash
python3 project-memory.py index --incremental
python3 project-memory.py remember --session SESSION_ID --kind outcome \
  --subject "run:summary" --payload '{"outcome":"..."}' --retention durable \
  --evidence path/to/changed-or-cited-file.ext:1-20
python3 project-memory.py session-close SESSION_ID \
  --outcome "one-line outcome" --evidence path/to/file.ext:1-20
python3 project-memory.py consolidate SESSION_ID
python3 project-memory.py status
python3 project-memory.py ledger-status
```

If Redis is unavailable, continue from files, disclose `cache_consulted: false`,
and still write the SQLite ledger. Never `FLUSHDB`/`FLUSHALL`, never reuse
another project's memory URL, never store secrets in memory. Durable records
are historical context only and never restore approval for Git, network,
hardware, or destructive writes.
