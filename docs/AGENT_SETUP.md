# Agent setup

## Existing project workflow

Preserve Project Memory v2.5. Follow `AGENTS.md` and `docs/PROJECT_MEMORY.md` at session start, after admitted-file changes, and before completion. Cache hits are discovery hints, not current source truth or permission to operate hardware. Never place secrets in memory.

Repository skills under `.grok/skills/` and `.agents/skills/` include the preserved `project-memory` skill plus environment, Cosmos teacher, imitation learning, Jetson export, rover safety and challenge evidence skills. These are development tools, not robot runtime dependencies.

The earlier setup recorded Grok Build 1.0.25. Verify the installed agent and selected model rather than assuming a product/model label specifies a local installer. Project trust controls whether project instructions, skills and hooks load. Only the owner grants folder trust.

## Environment ownership

| Environment | Use |
|---|---|
| `.venv-dev` | CPU training, export and development tests |
| `.venv` | Python 3.11 runtime inference and camera/telemetry integration |
| `.caferoomba/site-venv` | Optional website build/check tools |

Do not recreate or repurpose an existing environment without inspection. Never install `rover/requirements.txt` into the modern environments. Website generation must not execute/import robot control modules.

## MCP integrations

GitHub read/review tools and optional documentation servers can support development. Verify configured versus connected status. Do not install duplicate filesystem/shell/memory systems or add unreviewed `@latest` servers. Cloud administration and billable jobs require appropriate explicit authorization. MCP tools never belong in the real-time control path.

## Publication workflow

The website/docs are published separately from the uncommitted local Orin integration. Review the changed-file list before committing. Preserve original code, license and historical evidence; do not claim test success from an old memory entry. Follow [Website maintenance](WEBSITE.md) and [Status](STATUS.md).

If terminal access becomes blocked, stop retrying equivalent commands. Continue only permitted file editing/retrieval and document which execution checks and memory closures remain incomplete.
