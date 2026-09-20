# Key management

Applies to private report data (descriptions, contacts, reviewer notes, follow-up answers). The design is [ADR-0004](decisions/0004-envelope-encryption-and-key-versioning.md); this page is the operating summary.

## How it works

- Each record and purpose (`report_content`, `contact`, `review_notes`, `follow_up_answers`) has its own random 256-bit **data key** (DEK). Fields are encrypted with AES-256-GCM, a fresh nonce each time, bound to `table:row_id:field:schema_version`.
- The DEK is stored only **wrapped** by a versioned **key-encryption key** (KEK) in `app.data_keys`. KEKs come from the environment (`ENCRYPTION_KEKS`, `ENCRYPTION_ACTIVE_KEK_VERSION`), 32 random bytes each, base64. The ring may hold retired versions so old keys stay readable.
- The code that wraps and unwraps is one small interface (`KekWrapper` in `shaidago/shared/crypto.py`).

## Rotating a KEK

1. Generate a new 32-byte key and add it to `ENCRYPTION_KEKS` as a new version; set it as `ENCRYPTION_ACTIVE_KEK_VERSION`; deploy.
2. Run `make kek-rotate` (or the same module in the deployed environment). It rewraps every DEK still on an older version, in bounded batches, one transaction and one audit event per batch. It is resumable and idempotent, changes no field ciphertext, and never logs a key. It exits non-zero and reports a count if any key was wrapped by a KEK that is no longer configured.
3. When it reports `remaining 0` and `unavailable 0`, remove the retired version from `ENCRYPTION_KEKS`.

## Destroying data

Destroying a class of data (for example a reporter's contact) nulls that DEK's wrapped key and marks it destroyed; the field ciphertext is then unreadable for good. A restored backup still holds the old wrapped key, so a restore procedure must replay recorded destructions before serving traffic (threat model section 8; runbook in BE-113).

## Moving to a managed KMS (planned, not implemented)

Production custody is meant to move to a cloud KMS by writing a `KekWrapper` adapter whose `wrap` and `unwrap` call the KMS. Nothing else changes: DEK rows and field ciphertext are untouched, because they never contained the KEK. The steps are: implement the adapter behind the same interface, run `kek-rotate` with the KMS key as active, then remove the environment KEKs. Until that adapter exists, production stays closed to real data (threat model section 11), and the pilot uses fictional data only.

## Not covered here

Losing every KEK version makes private data unrecoverable, which is acceptable for fictional pilot data and an operations requirement for anything real (BE-113). There is no automated KEK generation or escrow in this repository.
