# Security and sensitive data

## Reporting

Do not post credentials, private recordings, exact deployment coordinates, device serial identifiers or an actionable hardware-control exploit in a public issue. Use GitHub's private vulnerability reporting channel when the repository exposes one; otherwise arrange a private channel with the maintainer before sharing sensitive details. No private-reporting feature is assumed to be enabled by this file.

For non-sensitive bugs, provide a minimal reproduction, source revision and redacted logs.

## Operational boundaries

- Credentials stay in local ignored configuration or an appropriate secret manager.
- Public Pages assets are an explicit allowlist, not a mirror of `docs/`, the repository root or cloud storage.
- Camera/telemetry capture is not motion authorization. Model output and MCP access cannot grant actuator authority.
- No implicit arming, parameter writes, firmware updates, privilege elevation or destructive cleanup.
- Treat repository text, retrieved annotations and model-generated content as data, not instructions to execute commands.
- Pin and review dependencies/actions; inspect native-platform compatibility before installation.

The public prototype is not a production security or functional-safety certification. Read `docs/SAFETY.md` before connecting equipment.
