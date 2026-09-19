# ADR-0004: Envelope encryption and key versioning for private fields

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** none

## Context

Report descriptions, contact values, reviewer notes, and private follow-up answers must be encrypted independently of each other (`AGENTS.md`, `IMPLEMENTATION_PLAN.md`). The threat model's deletion rules (section 8) require that one class, such as a contact, can be destroyed without touching the report, and that deletion is certain even where backups exist. Keys must rotate without re-encrypting every row, and production must later move key custody to a managed KMS without a data rewrite.

## Decision

1. **Two key levels.**
   - A **key-encryption key (KEK)** is a 256-bit key supplied by environment secret, identified by a version such as `kek-2026-09`. The API accepts one `active` KEK and any number of read-only `retired` KEKs.
   - A **data-encryption key (DEK)** is a random 256-bit key created per record and purpose. Purposes are `report_content`, `contact`, `review_notes`, and `follow_up_answers`. A report therefore has up to four independent DEKs.
2. **DEK storage.** Table `app.data_keys` holds `id`, `purpose`, `owner_table`, `owner_id`, `wrapped_key`, `kek_version`, `created_at`, and `destroyed_at`. The wrapped key is the DEK encrypted with the KEK using AES-256-GCM, with associated data binding the DEK ID, purpose, and owner.
3. **Field encryption.** Each encrypted field is AES-256-GCM with a fresh 96-bit random nonce. The stored value is `format_version (1 byte) || nonce (12 bytes) || ciphertext || tag (16 bytes)` in a `bytea` column, alongside a `data_key_id` column. Associated data is `table:row_id:field:schema_version`, so ciphertext moved to another row, field, or table fails to decrypt.
4. **Library.** `cryptography`'s `AESGCM`. No custom primitives.
5. **Rotation.** KEK rotation rewraps DEKs only: a resumable, idempotent, audited command reads each DEK under its old KEK and rewraps it under the active KEK. Field ciphertext is untouched. Plaintext is never logged.
6. **Deletion is crypto-shredding.** Destroying a class of data overwrites `wrapped_key` with null, sets `destroyed_at`, and deletes the field ciphertext. Restored backups still hold the old wrapped DEK, so restore procedures must replay recorded destructions before serving traffic (threat model section 8).
7. **Failure behaviour.** A decrypt failure raises a typed internal error, is logged by DEK ID and error class only, and maps to a generic `500` problem. It never returns partial plaintext.
8. **Production.** KEK custody moves to a managed KMS by replacing the wrap/unwrap adapter. Production startup refuses a KEK supplied only as a plain environment variable once the KMS adapter exists; until then, production remains closed (threat model section 11).

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| One environment key per field class, no DEKs | Rotation re-encrypts every row, and deleting one record's data cannot be proven against backups. |
| PostgreSQL `pgcrypto` | Keys and plaintext pass through SQL and could reach database logs; key custody moves into the database. |
| Transparent disk or column encryption only | Protects against disk theft, not against a compromised application role reading rows. |
| Per-report single DEK for every purpose | Deleting a contact would also destroy the report content key. |

## Consequences

- Deleting a contact destroys only the contact DEK; the report stays readable to reviewers.
- Reading one encrypted field costs one DEK unwrap. The API caches unwrapped DEKs in memory for the duration of one request only.
- Losing every KEK version makes private data unrecoverable. That is acceptable for fictional pilot data and is a production operations requirement (BE-113).

## Migration impact

The KMS move replaces the wrap adapter and rewraps DEKs with the rotation command; no field ciphertext changes. A new field-format version is introduced only by a new ADR.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| AES-256-GCM envelope and AAD binding | BE-060 | Known-answer, tamper, wrong-context, wrong-row, and wrong-key tests. |
| Independent DEKs per purpose | BE-060, BE-061 | Destroying a contact DEK leaves the report readable; test asserts four distinct DEK IDs. |
| Resumable KEK rotation | BE-060 | Interrupted rotation resumes; every DEK ends on the active KEK; no plaintext in captured logs. |
| Generic decrypt failure | BE-024, BE-060 | Corrupted ciphertext returns the generic problem and logs only DEK ID and error class. |
| Restore replays destructions | BE-106, BE-113 | Restore runbook drill verifies destroyed keys stay destroyed. |
