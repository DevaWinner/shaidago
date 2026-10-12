# Security scan triage

Last run: 2026-09-19 (BE-105). High or critical exploitable findings block release. Every suppression is narrow and explained. "Owner" is the repository maintainer until a team exists.

| Tool | How it runs | Result | Decision | Owner and deadline |
| --- | --- | --- | --- | --- |
| Ruff security rules (`S`) | `make backend-lint` (part of `make backend-verify` and CI) | No findings. Inline `noqa: S...` comments each state a reason (fixed SQL text, synthetic test values). | Pass. | Maintainer, continuous |
| Bandit | `make backend-security` | No findings after the run that flagged interpolated SQL constants in BE-094 (rewritten as literal statements). | Pass. | Maintainer, continuous |
| pip-audit | `make backend-security` | No known vulnerabilities in the locked dependencies. | Pass; rerun weekly (scheduled CI). | Maintainer, weekly |
| Gitleaks (history and tree) | `docker run zricethezav/gitleaks ... detect` and `.github/workflows/security.yml` | 6 findings on the first run, all from `generic-api-key`: the base64 placeholder `Y2hhbmdlLW1lLWNoYW5nZS1tZS1jaGFuZ2UtbWUtMzI=` (the text "change-me-change-me-change-me-32") in `.env.example` and the OpenAPI generator's synthetic settings, and two example UUID idempotency keys in tests. None is a credential; none reaches a deployed system (production refuses placeholder keys at startup). | Allowlisted narrowly in `.gitleaks.toml`; 0 findings after. | Maintainer, done |
| Semgrep 1.177.0 (`p/python`, `p/security-audit`) | `uvx semgrep`, and in `security.yml` | 0 findings over 172 files. **Limitation:** 9 files were only partially parsed because this Semgrep version does not yet understand Python 3.14's unparenthesised `except A, B:` form, so those files are less covered. | Pass with a named gap; re-run when Semgrep supports the syntax, and until then rely on Bandit, Ruff, Pyright, and CodeQL for those files. | Maintainer, before submission |
| CodeQL (`security-extended`) | `security.yml`, runs on GitHub | Not run in this environment (hosted service). Workflow written with pinned action SHAs. CodeQL's Python support for 3.14 syntax is unconfirmed. | **Pending** first run on GitHub. | Maintainer, before submission |
| Trivy (container and filesystem) | `make container-verify` locally; no GitHub Actions job | The GitHub container-build-and-Trivy job failed on 2026-10-12 because the current base image exposed newly published findings. The job was removed at the maintainer's direction; the local container verification remains available. | Hosted container scanning is disabled pending an explicit decision to restore and triage it. | Maintainer, before submission |
| Semgrep and CodeQL on the web app | Out of scope for the backend build order | Not applicable here. | Frontend gate. | |

The 2026-10-12 Trivy findings have not been triaged. Hosted container scanning is disabled, so this record must not be read as a current hosted-container security pass.
