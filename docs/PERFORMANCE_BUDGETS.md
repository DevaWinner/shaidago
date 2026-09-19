# Backend performance and resource budgets

Declared before measurement (BE-104). They are ceilings for catching an N+1 query, a missing index, an unbounded response, or a runaway resource, not a promise about production hardware. `services/platform/tests/integration/test_performance_budgets.py` enforces them; measured results are in [`docs/evidence/BE-104-performance.md`](evidence/BE-104-performance.md).

| Budget | Ceiling | Notes |
| --- | --- | --- |
| Public project list, p95 | 150 ms | 50 items from 600 projects |
| Public project detail, p95 | 150 ms | |
| Reviewer queue, p95 | 250 ms | 50 rows from 600 reports |
| Reviewer report detail, p95 | 300 ms | includes decryption |
| Tracking lookup, p95 | 600 ms | includes the intentional 250 ms equalisation floor |
| Password check (production Argon2id parameters) | 500 ms, one verification | sign-in p95 is dominated by this by design |
| SQL statements: public list / detail | 4 / 12 | must not grow with row counts |
| SQL statements: reviewer queue / detail | 6 / 16 | includes session resolution and audit |
| Response size: public list / reviewer queue / reviewer detail | 60 KB / 40 KB / 60 KB | page size is capped at 50 |
| One upload | 10 MB, at most 25 megapixels or 20 PDF pages, streamed to a temporary file | sanitise, scan, and store timeouts total at most 60 s |
| Worker | 2 concurrent requests and one request per second per host; job time limit 3 minutes; at most 4 retries | fetch total deadline 15 s |
| Database | pool of at most 10, statement timeout at most 10 s, connect timeout at most 10 s | |
| Readiness probe | 3 s | |
| Source chunk | at most 1000 characters | |

Reviewing a budget means changing this table and the test in the same change, with the reason.
