# ADR-0006: Evidence sanitation pipeline and hosted-demo scanner limitation

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** none

## Context

Reporters may attach photos or documents. Images can carry GPS coordinates and device details that identify the reporter; PDFs can carry author metadata, embedded files, and active content. The brief requires metadata removal before storage. The threat model (TM-T03, TM-D01, TM-I08) requires that raw bytes never reach durable storage, object keys reveal nothing, and hostile files cannot exhaust resources.

ClamAV needs roughly 1.5 to 3 GB of memory for its signature database. That is affordable locally and in CI, but not justified on the hosted demo, which accepts only fictional data. Railway containers do not share a filesystem, so raw uploads cannot be handed to the worker without placing them in shared durable storage, which the threat model forbids.

## Decision

1. **Where it runs.** Sanitation runs inside the API process during the submission request, in a bounded process pool (default two processes) with a per-file wall-clock limit. The event loop never decodes files. Raw bytes live only in a per-request temporary directory with a size cap.
2. **Accepted types.** JPEG, PNG, and WebP images, and PDF documents. Type is decided by magic bytes, not by extension or client MIME. Everything else is rejected. If time slips, PDF support is cut first (implementation plan scope-cut item 5) and the pipeline accepts images only.
3. **Default limits, configurable:** 3 files per report, 10 MiB per file, 25 MiB total, 40 megapixels per image, 50 pages per PDF.
4. **Images:** decode with Pillow under the pixel limit, apply EXIF orientation, then re-encode to a fresh file with no EXIF, IPTC, XMP, or GPS data. The output is a new encoding, not a stripped copy.
5. **PDFs:** open with `pikepdf`. Reject encrypted files. Remove document metadata, XMP, embedded files, JavaScript, actions, and form fields; save a new file. PDFs are only ever served as downloads (`Content-Disposition: attachment`).
6. **States.** Use the controlled-vocabulary values: `evidence_sanitation_state` moves `pending` → `processing` → `sanitised` | `rejected` | `failed`; `malware_scan_state` moves `pending` → `scanning` → `clean` | `malware_detected` | `scan_failed`, or `not_scanned_demo`.
7. **Scanning.** `SCANNER_MODE` is one of:
   - `clamd` (local, CI, staging, production): stream the sanitised artifact to clamd. If the scanner is unreachable, the file becomes `scan_failed` and is unavailable; the report is still accepted and the reporter is told that file was not attached.
   - `not_deployed` (hosted demo only): record `not_scanned_demo`, show that label to reviewers, and allow download of the sanitised file. Configuration validation refuses this mode when `APP_ENV=production`.
8. **Storage.** Only the sanitised artifact is uploaded, under a random 128-bit object key with no project, report, or person name. Metadata rows store the key, sanitised display name, sniffed type, size, and SHA-256 of the sanitised bytes.
9. **Cleanup.** The temporary directory is removed in a `finally` block on every outcome. A startup sweep removes any directory left by a crash.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| Sanitise in the worker from an object-store quarantine | Places raw, metadata-bearing files in durable shared storage, which the threat model forbids. |
| Strip metadata tags in place | Misses non-standard blocks and vendor segments; re-encoding is the reliable removal. |
| Client-side stripping only | The browser is untrusted; client processing is a usability layer only. |
| Run ClamAV on the hosted demo | Memory cost is not justified for fictional data; the limitation is labelled instead. |
| Accept Office documents or video | Much larger attack surface and parsing cost for no pilot need. |

## Consequences

- Submission latency grows with attachment size; the progress UI (FE build order) covers the wait.
- Two concurrent sanitations per API instance is the throughput ceiling; further uploads wait or get a retryable `503`.
- Reviewers on the hosted demo see `not_scanned_demo` on every file, which is honest about the limitation.

## Migration impact

Adding a file type requires a new sanitiser, fixtures, and an ADR amendment. Moving scanning to a dedicated service changes only the scanner adapter.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| GPS/EXIF removal by re-encoding | BE-064 | Fixture with GPS EXIF; stored output has no metadata segments. |
| Magic-byte typing and rejection | BE-064 | MIME spoof, polyglot, SVG with script, truncated file fixtures. |
| Resource limits | BE-063, BE-064 | Decompression bomb, oversized dimensions, page-count, and slow-stream fixtures. |
| Scanner modes | BE-020, BE-064 | EICAR detected in `clamd` mode; scanner-down gives `scan_failed`; production config refuses `not_deployed`. |
| Raw cleanup and random keys | BE-064 | Test asserts no temporary files after every outcome; storage spy asserts key entropy and content. |
