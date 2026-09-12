# Contributing to CafeRoomba

Thanks for contributing to an open-source agricultural robotics project. Keep changes small, testable and explicit about evidence.

## Before editing

Inspect the current branch and uncommitted work. Read `AGENTS.md`, `docs/PROJECT_MEMORY.md`, `docs/STATUS.md` and `docs/SAFETY.md`. Repository-local Project Memory is an agent workflow tool, not permission to operate hardware or reuse an old approval.

## Source changes

Use descriptive modules, typed boundary records and composition. Document units, coordinate frames, timing, I/O ownership and failure behavior. Constructors must not open devices. Do not import the historical GPIO/auto-arm scripts into the modern runtime.

Every feature should include deterministic tests and a status change tied to actual execution. Do not change an unsafe-condition test merely to make CI green. Do not mix documentation publication with unreviewed robot-control changes.

## Tests and pull requests

Use `.venv-dev` for learning/export and `.venv` for runtime integration. Include the exact test command and source/environment identity. Mark hardware tests explicitly and keep ordinary CI offline. Provide a short summary, affected interfaces, evidence, known limitations and rollback steps.

Keep mock, synthetic, real, cloud and target-device evidence separate. Never present test fixtures as navigation or agricultural performance.

## Documentation and website

Edit Markdown guides and the allowlisted site sources. Follow `docs/WEBSITE.md`. Add/verify relative links and accessible captions. Keep private recordings, credentials, device identifiers, exact coordinates, `.venv` and memory ledgers out of published assets.

## License

Preserve the original license and attribution. Contributions must be compatible with the project's license and with any dependency/model/media terms that apply. Do not silently relicense third-party code or model weights.
