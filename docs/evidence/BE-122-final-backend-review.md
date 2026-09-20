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

## Maintainer evidence, recorded 2026-09-19

Each item the automated review could not satisfy is now recorded. Who did what is stated exactly.

1. **Source audit — closed.** The maintainer (Aniekan Winner Anietie) states they reviewed and
   merged every pull request, including the source register. Alongside that, every recorded passage
   was re-fetched from its live page on 2026-09-19 and re-checked mechanically: all 11 passages
   across the three available sources still appear word for word in the visible page text, and every
   recorded passage hash matches. The two `access_restricted` sources were not re-fetched, because
   their access controls are not bypassed; they carry no verified fact and seed nothing. Reuse terms
   were not renegotiated: the register stores only metadata and short quoted passages with
   attribution, which is the same basis recorded when the register was built.
2. **Locale records — closed.** The four records in `data/qa-evaluation/golden-v1.json` name the
   maintainer as a fluent self-reported reviewer with the date and each dimension `preserved`. See
   [BE-085 live evaluation](BE-085-live-evaluation.md). It is not an independent second review, and
   nothing claims it is.
3. **GitHub CI — closed.** The backend and security workflows ran green on `main` after the pull
   requests were merged, including CodeQL, Semgrep, Gitleaks and the container Trivy scan.
4. **Staging smoke — see the staging record.** [BE-114](BE-114-staging-smoke.md) records the run,
   made against a temporary public domain on the staging `api` service that was removed afterwards,
   rather than through a registered SSH key.
5. **Live-provider evidence — closed.** [BE-097](BE-097-live-evidence.md) records live Brave and
   Groq runs, including two live pipeline runs that the deterministic validator rejected and failed
   closed, and [BE-085](BE-085-live-evaluation.md) records the live evaluation and its measured
   model-quality limitation.

An AI self-review still cannot substitute for a human judgement about whether a source says what
the register claims. What is claimed here is narrower and checkable: the passages are unchanged on
the live pages, and the maintainer has reviewed the register.
