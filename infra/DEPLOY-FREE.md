# Legacy: Vercel + Render (retired)

**FinSight production is Railway-only.** Do not deploy new environments with Vercel or Render.

| Guide | Use |
|-------|-----|
| **[infra/railway/DEPLOY.md](./railway/DEPLOY.md)** | Primary — API + frontend on Railway |
| **[infra/DEPLOY-FROM-GITHUB.md](./DEPLOY-FROM-GITHUB.md)** | End-to-end from GitHub → Railway + Supabase |

Database and Google auth stay on **Supabase**. Groq + Voyage stay as the free AI stack.

If you still have old Vercel/Render services from before the migration, delete them after your Railway URLs pass health checks and login works.
