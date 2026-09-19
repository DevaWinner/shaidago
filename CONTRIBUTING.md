# Contributing to ShaidaGo

ShaidaGo is a safety-sensitive civic technology proof of concept. Contributions must protect reporters, preserve source provenance, and keep the repository easy for hackathon judges to inspect and run.

## Before you start

- Read [`AGENTS.md`](AGENTS.md), [`PRODUCT.md`](PRODUCT.md), the [product brief](docs/PRODUCT_BRIEF.md), and the [implementation plan](docs/IMPLEMENTATION_PLAN.md).
- Check the current build gate and avoid adding features outside it.
- Check `git status` before editing and preserve unrelated work.
- For vulnerabilities or sensitive failure paths, use the private process in [`SECURITY.md`](SECURITY.md), not a public issue.

## Branch and commit workflow

Create a focused branch using `type/short-description`, for example `feat/project-directory` or `docs/source-register`.

Use Conventional Commit messages:

```text
feat: add cited project fact projection
fix: keep tracking codes out of request logs
docs: record source verification workflow
```

Keep commits small enough to review. Never commit secrets, real report data, unverified accusations, generated build output, or unrelated formatting changes.

## Development workflow

1. State the user outcome and acceptance criterion.
2. Add or update the smallest vertical implementation and its tests.
3. Regenerate contracts or clients from their source; never hand-edit generated output.
4. Run the relevant stack checks and the full repository gate when available.
5. Review the diff for public/private data leaks, unsupported claims, localisation gaps, accessibility regressions, and accidental files.
6. Update documentation and [`docs/AI_BUILD_LOG.md`](docs/AI_BUILD_LOG.md) when setup, behaviour, architecture, or material AI assistance changes.

The repository is currently pre-scaffold. Commands in the implementation plan are intended interfaces until Gate 1 adds them. Once present, `make verify` is the canonical judge-facing gate; stack-specific commands remain in their own package configuration.

## Pull requests

Every pull request must include:

- the user outcome and relevant build gate;
- a concise implementation summary;
- privacy, security, trust, and data-flow impact;
- API, schema, migration, environment, or deployment impact;
- exact verification commands and outcomes;
- screenshots or recordings for visible UI changes at mobile and desktop sizes;
- localisation and accessibility evidence for user-facing changes;
- known limitations and rollback/migration notes.

Do not merge while required checks fail, generated contracts differ, migrations fail from an empty database, or a high/critical exploitable vulnerability remains unresolved.

## Review priorities

Review in this order:

1. Reporter safety, privacy, authorisation, and public/private isolation.
2. Source grounding, citation validity, human-review gates, and neutral language.
3. Correctness, state transitions, migrations, error handling, and contract compatibility.
4. Accessibility, four-language completeness, low-bandwidth behaviour, and resilience.
5. Test quality, observability, maintainability, and performance.
6. Style and minor cleanup.

The root [`AGENTS.md`](AGENTS.md) contains the detailed blocking review rules and definition of done.
