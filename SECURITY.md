# Security policy

## Supported versions

Agentic is pre-1.0 software. Security fixes are applied to the latest commit on
`main`.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not
open a public issue for leaked credentials, unsafe automation behavior, or a
permission bypass.

Include:

- the affected commit
- reproduction steps
- the expected and observed behavior
- the potential impact
- a suggested mitigation, if known

## Security model

Agentic can control local applications and browsers. Treat every skill,
configuration change, and automation adapter as trusted code.

- Keep `.env` files and access tokens out of Git.
- Review actions before execution.
- Use the emergency stop shortcut: `Ctrl + Alt + Q`.
- Do not run unreviewed community skills.
- Do not expose the local API to the public internet.
- Keep external publishing and destructive actions behind explicit permission.

Privacy Mode masks the Agentic interface during a screen share. It does not
bypass recording software or operating-system monitoring.
