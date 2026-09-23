# Railway cutover checklist

Use this after creating the Railway project. Fill in your real domains.

## Your URLs (fill in)

| Role | URL |
|------|-----|
| Frontend | `https://________________.up.railway.app` |
| API | `https://________________.up.railway.app` |

## A. Railway services

### `finsight-api` (Root Directory: `backend`)

Copy these from your old Render service:

```
ENVIRONMENT=production
DATABASE_URL=<supabase session pooler :5432>
SUPABASE_URL=https://zibzsxwceivnziplciuq.supabase.co
REQUIRE_AUTH=true
DATABASE_FALLBACK_ENABLED=false
LLM_PROVIDER=groq
GROQ_API_KEY=<from Render / Groq console>
GROQ_MODEL=llama-3.1-8b-instant
EMBEDDING_PROVIDER=voyage
VOYAGE_API_KEY=<from Render / Voyage>
VOYAGE_MODEL=voyage-4-large
CORS_ORIGINS=https://<frontend>.up.railway.app
CHAT_RATE_LIMIT_PER_MINUTE=30
BETA_ALLOWED_EMAILS=<your emails>
```

Plus any Plaid/SMTP vars you already use.

### `finsight-web` (Root Directory: `frontend`)

Set **before first build**:

```
NEXT_PUBLIC_API_URL=https://<api>.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://zibzsxwceivnziplciuq.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

Then: Generate domain → set API `CORS_ORIGINS` → Redeploy API → Redeploy frontend if needed.

## B. Supabase Auth

**Authentication → URL Configuration**

- Site URL: `https://<frontend>.up.railway.app`
- Redirect URLs: add `https://<frontend>.up.railway.app/**`
- Keep: `http://localhost:3000/**`, `http://127.0.0.1:3000/**`
- Remove: old `*.vercel.app` entries after login works on Railway

## C. Verify

```bash
curl -sS https://<api>.up.railway.app/health
curl -sS https://<api>.up.railway.app/health/ready
curl -sS https://<api>.up.railway.app/capabilities
```

Browser:

1. Open frontend URL → Google sign-in
2. Dashboard loads data
3. Chat answers a finance question
4. Search page works / reindex if needed

## D. Landing page (optional)

```js
// docs/config.js
window.FINSIGHT_APP_URL = "https://<frontend>.up.railway.app";
```

## E. Retire Vercel + Render

Only after C passes for 24h:

1. Vercel → delete/suspend `fin-sight-ai-sepia` (or equivalent)
2. Render → delete/suspend `finsight-api-byrl`
3. Confirm nothing in README still lists those URLs (placeholders are fine until you paste Railway domains into README)

Full guide: [DEPLOY.md](./railway/DEPLOY.md)
