# BE-122 final backend evidence review

- **Date:** 19 September 2026
- **Branch:** `release-gate`
- **Status:** blocked on named human and hosted evidence
- **Data used:** repository fixtures and local ShaidaGo services only; no real report or live
  provider request

## Automated review completed

| Review | Result |
| --- | --- |
| Whole Git history secret scan | Gitleaks scanned 83 commits and about 3.67 MB with the committed narrow allowlist: no leak found. |
| Tracked environment/credential files | Only `.env.example` is tracked; no `.env`, private key, certificate bundle, local database, or credential export is tracked. |
| Candidate tracking codes, contacts, phones, signed URLs | Every candidate is a documented format example, visibly synthetic fixture/canary, generator constant, validation code, or dependency-lock false positive. No real contact, raw report, usable credential, or signed storage URL was found. |
| Public response schemas | Contract and integration checks cover all public catalogue, Q&A, and public-discovery response models; the explicit private-field denylist and runtime canaries pass. |
| Demo and replay records | Source-register reports carry `FICTIONAL REPORT FIXTURE` and `demo_only: true`; Q&A, embedding, discovery, and frontend fixtures are labelled synthetic/replay and use reserved example/test domains. |
| Known limitations | Prototype/non-emergency status, hosted scanner limitation, legal/privacy production gate, pending human language review, pending live providers, and pending staging smoke are visible in the root/docs/readmes and this record. |

## Source-register result

The dependency-free validator passes for six project records (three AMAC, three Bwari), their
recorded source references, exact passages where available, content hashes, last-checked date of
19 September 2026, fictional labels, and unresolved gaps. This automated result proves structural
and recorded-passage consistency only. It does not replace a person reopening every source,
checking the current page/document, confirming publisher/reuse terms, and comparing each public
wording to the evidence.

Three projects have no verified fact because the recorded source was access-restricted. Those
facts remain ineligible for seeding/publication. Most available facts remain
`awaiting_verification`; a URL or repeated claim is not treated as proof.

## Commands and results

```text
docker run ... gitleaks detect --redact             # 83 commits, no leaks
make backend-verify                                 # 1,999 passed; 1 live deselected; 94.03% coverage
python3 scripts/validate_controlled_vocabulary.py --self-test
python3 scripts/render_controlled_vocabulary.py --check
python3 scripts/validate_threat_model.py --self-test
python3 scripts/validate_decisions.py --self-test
python3 scripts/validate_source_register.py --self-test
python3 scripts/render_source_register.py --check   # all six passed
```

The targeted public-projection/shape/cache and contract tests are part of the canonical run. No
live OpenAI, Brave, or external source fetch was performed for this review.

## Required maintainer evidence

The backend release gate remains open until all applicable items are recorded:

1. A human source audit reopens every source for all six projects, checks each exact passage and
   public wording, reviews reuse terms, and records reviewer name and absolute date.
2. Fluent reviewers complete the four locale records in `data/qa-evaluation/golden-v1.json`.
3. The branch runs green in GitHub CI, including the canonical backend and security workflows.
4. The fictional staging smoke script runs inside Railway's private network after the maintainer
   registers an SSH key.
5. Explicitly authorised live-provider evidence is recorded, or the provider-dependent gates stay
   visibly open.

These items cannot be replaced by an AI self-review or deterministic fixture replay.
