# Architecture decision records

Each record captures one backend decision that is difficult to reverse: its context, the decision, rejected alternatives, consequences, migration impact, status, and the build tasks whose tests will enforce it. `scripts/validate_decisions.py --self-test` checks structure, numbering, this index, and every cited task ID.

A record is **accepted** when the decision is binding for implementation. Its controls remain planned until the owning task's tests pass. A changed decision gets a new record that supersedes the old one; accepted records are not rewritten except to fix errors that do not change the decision.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-modular-monolith-api-and-worker.md) | Modular monolith with API and worker entry points | accepted |
| [0002](0002-bff-authority-split-and-internal-service-authentication.md) | BFF/private API authority split and internal-service authentication | accepted |
| [0003](0003-postgresql-roles-row-security-and-no-returning-submission.md) | PostgreSQL roles, public views, row security, and the no-`RETURNING` submission path | accepted |
| [0004](0004-envelope-encryption-and-key-versioning.md) | Envelope encryption and key versioning for private fields | accepted |
| [0005](0005-tracking-code-and-reporter-credential-storage.md) | Tracking-code structure and keyed credential storage | accepted |
| [0006](0006-evidence-sanitation-pipeline-and-hosted-scanner-limitation.md) | Evidence sanitation pipeline and hosted-demo scanner limitation | accepted |
| [0007](0007-generated-openapi-browser-contract.md) | Generated OpenAPI contract for the browser boundary | accepted |
| [0008](0008-provider-isolation-replay-fixtures-and-live-tests.md) | Provider isolation, replay fixtures, and live-test policy | accepted |
| [0009](0009-groq-as-the-language-provider.md) | Groq as the language provider, and embeddings as a separate optional key | accepted |
| [0010](0010-local-embeddings-with-fastembed.md) | Local embeddings with FastEmbed and multilingual-e5-large | accepted |

## Template

```markdown
# ADR-NNNN: Title

- **Status:** proposed | accepted | superseded by ADR-NNNN | deprecated
- **Date:** YYYY-MM-DD
- **Task:** BE-___
- **Supersedes:** none | ADR-NNNN

## Context
## Decision
## Alternatives considered
## Consequences
## Migration impact
## Enforcement
```
