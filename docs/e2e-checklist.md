# FinSight AI — manual smoke checklist

Run against production (or `docker compose -f docker-compose.demo.yml up`) before tagging a release.

| # | Flow | Path / action | Expect |
|---|------|---------------|--------|
| 1 | Sign in | Google or email link → `/auth/callback` | Dashboard loads with your accounts |
| 2 | Demo data | New empty account signs in | Starter data appears after sync |
| 3 | Chat | Ask "How much did I spend on groceries last month?" | Chat appears in the sidebar at once; reply streams with source chips |
| 4 | Concurrent chats | Click three suggested questions quickly | Three separate chats, each answered |
| 5 | Evidence | Click a source chip | Drawer shows the transactions behind the amount |
| 6 | Weekly brief | Home → "Ask advisor" | Opens a chat and answers without an error flash |
| 7 | Search | `/search` "Uber last month" | Matching transactions |
| 8 | Leaks | `/leaks` | Findings list; dismiss and draft a cancellation letter |
| 9 | Planner and forecast | `/planner`, `/forecast` | TFSA / OSAP results and Monte Carlo bands render |
| 10 | Delete chat | Delete from the sidebar | Confirmation dialog; chat does not come back on refresh |
| 11 | Export | Settings → export | JSON download of your data |
