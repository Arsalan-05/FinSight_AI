/**
 * Playwright smoke stubs — 10 critical flows (Phase 10).
 *
 * Documentation-only until `@playwright/test` is installed. Mirror rows in
 * `docs/e2e-checklist.md`. When ready:
 *
 *   cd frontend && npm i -D @playwright/test && npx playwright install
 *   BASE_URL=http://localhost:3000 npx playwright test
 *
 * Convert each entry below to `test.skip("…", async ({ page }) => { … })`.
 */

export const SMOKE_FLOWS = [
  { name: "auth sync → dashboard", path: "/" },
  { name: "demo provision for empty user", path: "/" },
  { name: "chat SSE + evidence chips", path: "/chat" },
  { name: "evidence drawer from chip click", path: "/chat" },
  { name: "leaks list dismiss/resolve", path: "/leaks" },
  { name: "leak action draft", path: "/leaks" },
  { name: "planner pages render", path: "/planner" },
  { name: "forecast bands render", path: "/forecast" },
  { name: "search returns transactions", path: "/search" },
  { name: "settings / PIPEDA export", path: "/settings" },
] as const;
