# Security policy

## Prototype status

ShaidaGo is a hackathon proof of concept, not a production whistleblower service or emergency channel. Do not submit real allegations, identities, contact information, confidential documents, or sensitive evidence to the application, repository, issues, discussions, demo, or test environments.

Only the current `main` branch and the current hosted demonstration, when one exists, are in scope for fixes. No security bounty is offered.

## Report a vulnerability privately

Do not open a public issue for a suspected vulnerability or include exploit details in public pull requests.

Use GitHub's private vulnerability reporting for this repository:

<https://github.com/DevaWinner/shaidago/security/advisories/new>

Include:

- the affected component, commit, or URL;
- a minimal reproduction using synthetic data;
- the expected and observed result;
- the likely impact, especially any public/private data boundary involved; and
- any suggested mitigation, if known.

Do not access, retain, modify, or disclose another person's data while testing. Stop testing if a reproduction could expose real data or disrupt service.

## Security invariants

The following are treated as release-blocking:

- unauthorised access to reports, contacts, evidence, internal notes, reporter-handle links, or private discovery;
- private content entering public responses, caches, logs, analytics, metrics, AI prompts, or external search queries;
- tracking-code or credential enumeration and distinguishable private-record lookup errors;
- publication of an unreviewed allegation, discovered source, or AI-generated claim;
- unsafe file persistence, metadata leakage, server-side request forgery, or prompt injection that crosses a trust boundary;
- committed credentials or production data.

Detailed engineering controls and required adversarial tests are defined in [`AGENTS.md`](AGENTS.md) and [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## Secrets and test data

- Commit only `.env.example` placeholders; real values belong in local or hosted secret stores.
- Use synthetic identities, fictional reports, and safe test fixtures.
- Project seed facts must come from cited public sources and must avoid unsupported accusations.
- Revoke and rotate a credential immediately if it enters Git history, logs, screenshots, or an issue. Removing the visible text from a later commit is not sufficient.
