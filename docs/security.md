# Security & compliance

## Threat model (STRIDE)

| Asset | Spoofing | Tampering | Repudiation | Info disclosure | DoS | Elevation |
|-------|----------|-----------|-------------|-----------------|-----|-----------|
| JWT / session | JWKS verify, expiry | — | audit_log | short-lived tokens | rate limit | require auth |
| Transactions | scoped queries + RLS | RLS + app scoping | audit tool calls | PII redact before LLM | upload limits | no service-role in client |
| Chat / tools | treat tool output as data | delimit tool blocks | audit_log | strip injection patterns | tool-loop cap 6 | privacy mode → Ollama only |
| Plaid tokens | — | encrypt at rest | — | never log tokens | — | rotate keys |
| CSV export | — | formula-injection sanitize | — | export is user-owned | size/MIME limits | — |

## Mitigations

| Control | Location |
|---------|----------|
| Row-Level Security | [`infra/rls/policies.sql`](../infra/rls/policies.sql) — `auth.uid()` → `users.auth_id` |
| PII redaction | `backend/agent/privacy/redact.py` — emails, phones, account #s, e-Transfer names |
| Prompt-injection defense | `backend/agent/privacy/injection.py` — tool delimiters + pattern strip |
| Privacy mode | `privacy_mode: bool` in config — **forces Ollama** (no cloud LLM) |
| Audit log | `AuditLog` model + `GET /audit` |
| Security headers | CSP, HSTS (prod), X-Frame-Options, nosniff |
| CSV formula sanitize | `app/csv_sanitize.py` — applied on `GET /auth/me/export` string fields |
| Request correlation | `X-Request-ID` middleware + `request_id` on structured logs |
| Dependency audits | [`.github/workflows/security.yml`](../.github/workflows/security.yml) — weekly `pip-audit` and `npm audit` |

## Privacy mode

```bash
PRIVACY_MODE=true
```

When enabled, `settings.effective_llm_provider` always returns `ollama`. Transaction text and tool results stay on-machine. Embeddings may still use Voyage unless you also set `EMBEDDING_PROVIDER=ollama`.

## RLS notes

- FastAPI connects as a privileged DB role and **bypasses** RLS — app-level `user_id` scoping remains mandatory.
- RLS protects PostgREST / Supabase client access as defense-in-depth.
- Policies cover: accounts, transactions, chat_sessions, leak_findings, budgets, notifications.

## PIPEDA mapping

| Principle | Feature |
|-----------|---------|
| Consent | Google / email sign-in behind an invite allowlist; privacy page |
| Access | `GET /auth/me/export` (formula-sanitized strings) |
| Deletion | `DELETE /auth/me` |
| Retention | Users delete individual chats or the whole account at any time |
| Safeguards | RLS, encryption at rest (Supabase), PII redaction, privacy mode |

## Key management

- Plaid `access_token` encrypted at rest (Fernet / app crypto)
- Keys live only in Railway variables and the gitignored `.env`; history is scanned for key patterns before each release tag
- Rotate a key immediately if it is ever pasted anywhere else; never put secrets in docs

## Reporting

See [SECURITY.md](../SECURITY.md).
