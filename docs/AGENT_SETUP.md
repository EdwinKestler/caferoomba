# Agent setup

Grok Build 1.0.25. Selected model is whatever this session was launched with
(user asked for Grok 4.7 as a backend label; this agent did not download a
separate package).

## Skills

Repository skills live under `.grok/skills/` (copied to `.agents/skills/`):

- `project-memory` (preserved)
- `caferoomba-environment`
- `caferoomba-cosmos-teacher`
- `caferoomba-imitation-learning`
- `caferoomba-jetson-export`
- `caferoomba-rover-safety`
- `caferoomba-challenge-evidence`

This coding session loaded the new CafeRoomba skills after they were written.
`grok inspect` from an **untrusted** CLI process reports `Project trusted: no`
and therefore omits project instructions, project skills, and project hooks.
Do not grant blanket `/hooks-trust` unless Edwin does so.

## MCP

| Server | Configured | Connected in this session | Notes |
|---|---|---|---|
| GitHub | reused existing session integration (93 tools) | yes | read tools used; no project `npx @latest` added |
| xAI docs | `.grok/config.toml` → `https://docs.x.ai/api/mcp` | verify with `grok mcp doctor` after folder trust | no secrets |
| Google Cloud MCP | omitted | no | spending allowance zero |
| Cloudflare plugin MCPs | user plugin | docs healthy; API/builds/bindings/observability need auth | unrelated to robot runtime |

Cleanup: delete `.grok/config.toml` `[mcp_servers.xai-docs]` or `grok mcp remove --scope project xai-docs`.

## Local Python

Isolated `.venv-dev` (Python 3.11). Do not install `rover/requirements.txt`.
`scripts/bootstrap.py` is dry-run unless `--apply`.
