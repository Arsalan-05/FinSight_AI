# Cost model

What FinSight costs to run at personal and small-demo scale (CAD, monthly).

| Component | Plan | Cost now | At ~1k monthly users |
|-----------|------|----------|----------------------|
| Railway (web + API) | Hobby | ~$7 | $10–25 |
| Supabase (Postgres, Auth) | Free | $0 | $0–35 (Pro when the 500 MB database fills) |
| Groq (`gpt-oss-20b` basic, `gpt-oss-120b` fallback) | Free tier | $0 | $0–10 |
| Anthropic (`claude-sonnet-4-6`, heavy turns only) | Pay as you go | a few dollars | $10–50 |
| Voyage (`voyage-4-large` embeddings) | Free token allowance | $0 | ~$0 |
| Plaid | Sandbox | $0 | per-item pricing if production access is enabled |

## What keeps it cheap

- **Tier routing** ([ADR 0005](./adr/0005-model-routing.md)): spend lookups, which are most turns, stay on Groq. Claude only sees planning, coaching and multi-step questions.
- **No LLM arithmetic**: totals come from SQL and the `calculate` tool, so prompts stay short and retries are rare.
- **Semantic cache** for repeated searches, and one embedding per transaction computed once at ingest.
- **Groq 429s fall straight through to Claude** instead of waiting out the rate-limit window, trading a little cost for latency.
