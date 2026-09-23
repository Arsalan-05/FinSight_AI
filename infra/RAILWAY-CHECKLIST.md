# Railway production checklist

Live FinSight production URLs (Railway + Supabase).

| Role | URL |
|------|-----|
| Frontend | `https://finsightai-production-43d0.up.railway.app` |
| API | `https://finsight-api-production-2aee.up.railway.app` |
| Database + Auth | Supabase (`zibzsxwceivnziplciuq`) |

## A. API service (`finsight-api`)

Root Directory: `backend`

```
ENVIRONMENT=production
DATABASE_URL=<supabase session pooler :5432>
SUPABASE_URL=https://zibzsxwceivnziplciuq.supabase.co
REQUIRE_AUTH=true
DATABASE_FALLBACK_ENABLED=false
LLM_PROVIDER=groq
GROQ_API_KEY=<from Groq console>
GROQ_MODEL=llama-3.1-8b-instant
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
Set **before** each build that needs new public env:

```
NEXT_PUBLIC_API_URL=https://finsight-api-production-2aee.up.railway.app
NEXT_PUBLIC_SITE_URL=https://finsightai-production-43d0.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://zibzsxwceivnziplciuq.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

`NEXT_PUBLIC_SITE_URL` must be the public Railway app URL (not `0.0.0.0`). Redeploy frontend after setting it.

## C. Supabase Auth

**Authentication → URL Configuration**

- Site URL: `https://finsightai-production-43d0.up.railway.app`
- Redirect URLs:
  - `https://finsightai-production-43d0.up.railway.app/**`
  - `http://localhost:3000/**`
  - `http://127.0.0.1:3000/**`

## D. Verify

```bash
curl -sS https://finsight-api-production-2aee.up.railway.app/health
curl -sS https://finsight-api-production-2aee.up.railway.app/health/ready
curl -sS https://finsight-api-production-2aee.up.railway.app/capabilities
```

Browser:

1. Open frontend → Google sign-in
2. Dashboard loads data
3. Chat answers a finance question
4. Search works / reindex if needed

## E. Landing page (optional)

```js
// docs/config.js
window.FINSIGHT_APP_URL = "https://finsightai-production-43d0.up.railway.app";
```

Full guide: [DEPLOY.md](./railway/DEPLOY.md)
