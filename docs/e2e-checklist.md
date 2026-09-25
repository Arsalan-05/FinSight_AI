# FinSight AI — E2E smoke checklist

Manual / Playwright flows for Phase 10. Mark each pass before a release.

| # | Flow | Path / action | Pass? |
|---|------|---------------|-------|
| 1 | Auth sync | Sign in → `/auth/callback` → dashboard loads | |
| 2 | Demo provision | Empty user → starter data appears after sync | |
| 3 | Chat SSE | `/chat` ask spend question → streamed reply + evidence chips | |
| 4 | Evidence drawer | Click `[[$…\|ev_N]]` chip → drawer shows tool result | |
| 5 | Leaks list | `/leaks` shows findings; dismiss / resolve | |
| 6 | Leak draft | Generate cancellation / fee-reversal draft | |
| 7 | Planner | `/planner` registered / OSAP / what-if renders | |
| 8 | Forecast | `/forecast` Monte Carlo bands render | |
| 9 | Search | `/search` hybrid query returns transactions | |
| 10 | Settings / export | Profile + PIPEDA export download | |

## Playwright stubs (optional)

When Playwright is added (`npx playwright install`), mirror each row as `test.skip` in `frontend/e2e/smoke.spec.ts`. Until then, run this checklist against staging or `docker compose -f docker-compose.demo.yml up`.
