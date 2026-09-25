# Load test results template

Fill this after running `k6 run infra/load/chat.js` (see [infra/load/chat.js](../infra/load/chat.js)).

## Run metadata

| Field | Value |
|-------|-------|
| Date (UTC) | |
| Environment | staging / production / local |
| `BASE_URL` | |
| k6 version | |
| VUs | 50 |
| Duration | 30s |
| Chat included? | yes / no (`AUTH_TOKEN` set?) |
| Commit SHA | |

## Command

```bash
BASE_URL=https://… AUTH_TOKEN=… k6 run infra/load/chat.js
```

## Results

| Metric | Target | Observed | Pass? |
|--------|--------|----------|-------|
| http_req_failed | < 5% | | |
| http_req_duration p95 | < 2000 ms | | |
| http_req_duration p99 | — | | |
| iterations | — | | |
| `/health` checks | 100% | | |
| `/chat` (if run) not 5xx | — | | |

## Notes / bottlenecks

- DB pool size:
- LLM provider / rate limits:
- Observed errors:
- Follow-ups:

## Raw k6 summary

Paste `k6` end-of-run summary here.
