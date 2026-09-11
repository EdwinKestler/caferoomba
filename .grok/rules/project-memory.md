# Project Memory (always on)

This repo's Project Memory v2.5 is **mandatory on every run**. Do not treat it
as optional and do not skip "small" tasks.

1. Start: `./scripts/project_memory_agent.sh ensure`, then `status`, `recall`,
   `search`, and `session-start`.
2. During: `search`/`recall` before reusing a decision; `index --incremental`
   after changing admitted files; `remember` durable facts with evidence.
3. End: `index --incremental`, `session-close`, `consolidate`, `status`,
   `ledger-status` before the final reply.

Protocol: `AGENTS.md` and `docs/PROJECT_MEMORY.md`.
