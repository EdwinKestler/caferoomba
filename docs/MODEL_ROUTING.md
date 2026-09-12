# Repository model routing

Policy source: `GPTagentTree.png`. Text instructions: `AGENTS.md`.

| Task | Agent | Model | Reasoning |
| --- | --- | --- | --- |
| Orchestrate, integrate, verify | Root | gpt-6-astra | medium |
| Bounded investigation | explorer | gpt-5.6-luna | max |
| Implementation and tests | worker | gpt-5.6-sol | high |
| Focused lookup | researcher | gpt-5.6-luna | max |
| Independent review, only if needed | reviewer | gpt-6-astra | xhigh |

## Operation

Start a new Codex session from this trusted repository:

```bash
codex -C /home/kestl/github/caferoomba
```

`.codex/config.toml` sets the root and fallback child defaults.
`.codex/agents/*.toml` defines named role models and reasoning efforts.
The root classifies subtasks using AGENTS.md and selects only useful roles.
Small tasks can remain entirely with root. This is instruction-driven routing
with configured role defaults, not a deterministic task classifier or a security
boundary. Command-line overrides and managed runtime policy can supersede it.

For runtimes exposing explicit spawn overrides instead of custom named agents,
AGENTS.md requires the same model/effort pairs with a minimal-context task.
A full-history fork may force parent model inheritance; avoid it for these roles.
Do not silently fall back if a model or reasoning level is unavailable.

Existing sessions may retain their original model and agent configuration.
Restart to load these files, and inspect the actual child model/effort in session
metadata when verifying a real delegated task. Parsing the TOML does not prove
that the current account can execute every model. No paid inference is required
to install or statically validate this configuration.

Run `python -m pytest tests/test_model_routing.py` to validate the root defaults,
all four exact role/model/effort mappings, required custom-agent fields and the
absence of repository permission overrides. This is a policy-drift regression,
not an account-access or runtime-enforcement test. Configuration structure was
checked against the official custom-agent documentation on 2026-09-12.

Sandbox permissions independently control execution access. These files do not
disable sandboxing or approval prompts. Research/exploration/review agents avoid
application edits by instruction while retaining inherited permissions for the
mandatory local Project Memory ledger. Role instructions are not OS enforcement.

For hard enforcement across all entrypoints, a separate dispatcher must validate
each requested role/model/effort before launching it and record actual execution
metadata. That is outside this native repository configuration.

References: [custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [configuration](https://learn.chatgpt.com/docs/config-file/config-reference).
