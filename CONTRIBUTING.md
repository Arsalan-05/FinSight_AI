# Contributing to FinSight AI

FinSight is a finished personal project (v2.0.0). Bug reports and small fixes are welcome as issues or focused pull requests; new features are out of scope.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(leaks): add FX markup detector
fix(agent): strip unverified dollar amounts
docs(evals): publish baseline model matrix
test(planning): cover FHSA lifetime cap edge case
chore(ci): add eval smoke gate
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`, `security`.

## Development

```bash
cp .env.example .env
docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head
uv run pytest -q
cd ../frontend && npm ci && npm run lint && npm run type-check
```

Nothing merges without tests. A change to money math or retrieval must keep `python -m evals.run --subset full --dry-run` passing.

## Pull requests

1. Branch from `main` (`feat/...`, `fix/...`).
2. Keep PRs focused; prefer small reviewable diffs.
3. CI must be green: lint, types, tests, eval smoke.
4. Add a line to `CHANGELOG.md` when the change is user-facing.

## Code style

- Backend: Ruff + mypy (strict on `app/`, `agent/`, `db/`, `rag/`, `insights/`).
- Frontend: ESLint + TypeScript strict.
- Prefer deterministic Python for money math; LLMs explain, they do not compute.
