# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 2.0.x   | Yes |
| < 2.0   | No |

## Reporting a vulnerability

Do **not** open a public GitHub issue for security bugs.

Email the owner at the address on the GitHub profile, or open a private security advisory on the repository. Include:

- Affected endpoint or component
- Steps to reproduce
- Impact (data access, injection, auth bypass)
- Suggested fix if you have one

You should receive an acknowledgment within 7 days.

## Secrets

- Never commit `.env`, service-role keys, or Plaid tokens.
- Keys live only in Railway variables and the gitignored `.env`; git history is scanned for key patterns before each release.
- See `docs/security.md` for the STRIDE threat model and PIPEDA mapping.

## Scope notes

FinSight handles personal financial data. Treat auth bypass, cross-user data leaks, and prompt-injection that exfiltrates transactions as critical.
