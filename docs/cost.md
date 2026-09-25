# Cost model

Approximate monthly cost at personal / demo scale. Update after Phase 8 load test.

| Component | Free tier / plan | Est. at 1k MAU |
|-----------|------------------|----------------|
| Railway (web + API) | Hobby | $5–20 |
| Supabase | Free → Pro | $0–25 |
| Groq (basic + heavy fallback) | Generous free | ~$0–5 |
| Claude Sonnet (heavy tier) | Pay-as-you-go | ~$5–40 (routing keeps most turns on Groq) |
| Voyage | 200M tokens free | ~$0 |
| Plaid | Sandbox free | Production TBD |
| Domain | — | ~$15/yr |
| Sentry / Langfuse | Free tiers | $0 |

**Routing:** basic → Groq 8B (cheap); heavy → Claude when keyed (ADR 0005). Target: document $ per 1,000 chat queries from eval cost metrics.
