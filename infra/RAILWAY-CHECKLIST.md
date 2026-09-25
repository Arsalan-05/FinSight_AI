# Railway production checklist

Live FinSight production URLs (Railway + Supabase).

| Role | URL |
|------|-----|
| Frontend | `https://finsightai-production-43d0.up.railway.app` (custom domain TBD) |
| API | `https://finsight-api-production-2aee.up.railway.app` |
| Database + Auth | Supabase (project ref **not** published — use dashboard) |

## A. API service (`finsight-api`)

Root Directory: `backend`

```
ENVIRONMENT=production
DATABASE_URL=<supabase session pooler :5432>
SUPABASE_URL=https://<project-ref>.supabase.co
REQUIRE_AUTH=true
DATABASE_FALLBACK_ENABLED=false
LLM_PROVIDER=groq
GROQ_API_KEY=<from Groq console>
GROQ_MODEL=openai/gpt-oss-20b
GROQ_HEAVY_MODEL=openai/gpt-oss-120b
LLM_ROUTING_ENABLED=true
ANTHROPIC_API_KEY=<from console.anthropic.com>   # Claude heavy tier
ANTHROPIC_MODEL=claude-sonnet-4-6
EMBEDDING_PROVIDER=voyage
VOYAGE_API_KEY=<from Voyage>
VOYAGE_MODEL=voyage-4-large
CORS_ORIGINS=https://finsightai-production-43d0.up.railway.app
CHAT_RATE_LIMIT_PER_MINUTE=30
BETA_ALLOWED_EMAILS=<your emails>
```

Plus any Plaid/SMTP vars you use.

## B. Frontend service (`finsight-web`)

Root Directory: `frontend`  
**Important:** the browser must **not** call the API hostname directly (Safari often fails that cross-origin fetch even on hotspot). Use the same-origin proxy:

```
NEXT_PUBLIC_API_URL=/backend
API_PROXY_TARGET=https://finsight-api-production-2aee.up.railway.app
NEXT_PUBLIC_SITE_URL=https://finsightai-production-43d0.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

Both `NEXT_PUBLIC_API_URL` and `API_PROXY_TARGET` must be set **before** the Docker build (Railway rebuild after changing them).

### Frontend variables (must match roles)

| Variable | Must be |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | `/backend` (same-origin proxy path) |
| `API_PROXY_TARGET` | Full Railway **API** URL |
| `NEXT_PUBLIC_SITE_URL` | **Frontend** host |

Flow: Browser → `https://frontend/backend/...` → Next rewrite → Railway API. Same pattern as a single-service app.

## C. Pre-public release

- [ ] Buy custom domain and point at Railway
- [ ] Rotate every key that ever appeared in git history (Groq, Voyage, Supabase service role, Plaid)
- [ ] Run `gitleaks detect` and `trufflehog` over full history
- [ ] Confirm docs contain no project refs or secrets

## D. Health

```bash
curl https://finsight-api-production-2aee.up.railway.app/health/db
# After proxy deploy, this should also work via the website:
curl -I https://finsightai-production-43d0.up.railway.app/backend/health
```

Expect API `connected: true`, `schema_ready: true`.
