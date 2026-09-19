# BE-104 measured performance

- **Date:** 2026-09-19
- **Command:** `uv run --env-file ../../.env pytest tests/integration/test_performance_budgets.py -s` from `services/platform` (also part of `make backend-verify`).
- **Dataset:** the synthetic public project plus 600 scaled synthetic projects with English translations and 600 synthetic private reports (encrypted-shaped placeholders), one real fictional report with contact and one attachment; 120 sequential requests per endpoint after one warm-up request.
- **Environment:** a developer laptop (macOS, Darwin 27), Python 3.14, PostgreSQL 18 with pgvector and Redis in Docker Compose on the same machine, requests made in process through the ASGI app (no network hop, so these are server-side times, not browser times), real database roles.
- **Accepted variance:** budgets are 10 to 40 times the measured values, so run-to-run and machine-to-machine noise cannot fail the suite; a real regression (a lost index or an N+1) will.

| Endpoint | p95 | Response | SQL statements |
| --- | --- | --- | --- |
| `GET /v1/projects?limit=50` | 4.0 ms | 18.4 KB | 1 |
| `GET /v1/projects/{slug}` | 3.8 ms | 0.4 KB | 6 |
| `GET /v1/reviewer/reports?limit=50` | 6.2 ms | 16.1 KB | 2 |
| `GET /v1/reviewer/reports/{id}` | 5.7 ms | 0.9 KB | 7 |
| `POST /v1/report-status:lookup` | 255.6 ms | small | (about 250 ms is the intentional equalisation floor) |

Statement counts are identical with and without the 600 scaled projects and reports, which is the check for a hidden N+1.

Not measured: hosted latency, concurrent multi-user load, upload memory under a real 10 MB file (the limits are asserted, and the file is spooled to disk), and Argon2 cost on the Railway instance size (the check uses the developer machine; the production parameters must be re-timed on the deployed size before launch). No optimisation was made, because nothing approached its budget.
