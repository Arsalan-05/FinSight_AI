# FinSight AI — Freeze / maintenance mode (v2.0.0)

Stable target: **v2.0.0**. After tag, treat the tree as maintenance-only unless a security or data-loss bug lands.

## Pre-tag checklist

- [ ] `cd backend && uv run pytest -q` green on critical suites (propertyish, calculate, leaks, planning, evidence, security)
- [ ] `uv run python -m evals.run --subset smoke --dry-run` exits 0
- [ ] Frontend `npm run lint && npm run type-check && npm run build`
- [ ] `docs/metrics.json` regenerated / reviewed
- [ ] CHANGELOG `[2.0.0]` section complete
- [ ] Secret scan clean; no keys in git history of the tag
- [ ] Dependabot open PRs triaged (security first)
- [ ] Keepalive workflow has `FINSIGHT_HEALTH_URL` set (or accepted skip)
- [ ] Demo path verified: `docker compose -f docker-compose.demo.yml up --build`

## Tag & pin

```bash
git tag -a v2.0.0 -m "FinSight AI v2.0.0 — stable freeze"
git push origin v2.0.0
```

Pin Railway / local to the tag or the commit SHA of the release. Prefer lockfile digests already in `uv.lock` / `package-lock.json`.

## Maintenance mode rules

1. **No feature PRs** into `main` without an explicit unfreeze decision.
2. **Allowed:** security patches, dependency CVEs (Dependabot), docs typos, broken-deploy hotfixes.
3. **Evals gate stays on** in CI — do not delete the smoke dry-run step.
4. **Model changes** only via config/env (tiered Groq/Claude/Ollama), not prompt rewrites that change money math.
5. **Schema:** new Alembic revisions only for critical fixes; document in CHANGELOG.

## Unfreeze

Document the reason, bump toward `v2.1.0`, reopen Phase items in `docs/v2-issues.md`, and update README status off “stable target v2.0.0”.
