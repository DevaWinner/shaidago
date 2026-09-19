# ADR-0005: Tracking-code structure and keyed credential storage

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** none

## Context

An anonymous reporter checks status with a code they received once. The code is the only credential, so it must be unguessable, easy to copy by hand on a phone, resistant to typos, and never stored in a form that reveals it. The optional reporter handle (implementation plan, "Anonymous reporter handles") adds a second credential pair that must carry no identity or recovery data. The threat model (TM-S02, TM-I02) requires enumeration resistance and generic failures.

## Decision

### Tracking code

1. **Format:** `SG-XXXXX-XXXXX-XXXXX-XXXXX-C`. The 20 body characters encode 100 random bits in Crockford Base32 (`0-9`, `A-Z` without `I`, `L`, `O`, `U`). `C` is one check character.
2. **Randomness:** `secrets.token_bytes`, behind an injectable source for tests.
3. **Checksum, version 1:** Luhn mod 32 over the 20 body symbols, emitted in the same alphabet. It detects every single-character substitution and most adjacent transpositions without adding symbols that are hard to type. The checksum version is stored so a future algorithm can coexist.
4. **Normalisation:** uppercase; remove spaces and hyphens; if 23 characters remain, require and strip the leading `SG` (both are valid Base32 symbols, so the prefix is recognised by length, never by content alone); require exactly 21 characters; map Crockford aliases `O`→`0` and `I`/`L`→`1`; reject `U` and any other character. The checksum is validated after normalisation and before any database work, so an alias mapping can never match a different code silently.
5. **Storage:** only `HMAC-SHA-256(pepper[v], "sg-track-v1:" + normalised_body_and_check)` in `app.report_tracking_keys`, with `pepper_version` and `checksum_version`. The HMAC column has a unique index for indexed lookup.
6. **Pepper rotation:** peppers are environment secrets with versions. Lookup tries the active pepper, then retired peppers; a match under a retired pepper is rehashed to the active one in the same transaction. A retired pepper is removed once no rows use it.
7. **Exposure:** the raw code appears once, in the no-store submission response. It is never logged, placed in a URL, cookie, or browser storage, or echoed by lookup.

### Lost-response retry without storing the code

BE-063 requires that a retried submission with the same `Idempotency-Key` returns the same result, but the result contains the raw tracking code, which must never be stored. The two rules are reconciled this way:

1. The client generates the idempotency key as a random UUIDv4 and holds it in memory only for the retry window. It is never written to browser storage, a URL, or logs.
2. The server stores `HMAC-SHA-256(idempotency_pepper, key)` for lookup, the request fingerprint, and the response sealed with AES-256-GCM under a key derived from the raw idempotency key with HKDF-SHA-256. The server cannot open the sealed response without the client's key.
3. A matching retry within 15 minutes re-derives the key, opens the sealed response, and returns the same code. After 15 minutes, the sealed response is deleted and a retry returns a generic "submission already received" problem without a code.
4. A key reused with a different request fingerprint returns the `409` idempotency-conflict problem.

A database leak therefore exposes no tracking code, while a reporter whose connection drops after submitting still receives their code.

### Optional reporter handle

1. **Handle:** `SG-H-XXXX-XXXX`, 40 random bits in Crockford Base32. It is an identifier, not a secret.
2. **Passphrase:** six words drawn with `secrets.choice` from the committed EFF long wordlist (7,776 words, about 77.5 bits). Users cannot choose either value.
3. **Storage:** handle plus Argon2id hash of the passphrase, using the central Argon2 parameters shared with reviewer passwords (BE-050). The table has no email, phone, IP, device, recovery, or profile column.
4. **Verification:** only at report submission, handle report listing, and handle deletion. No session is created.

### Why HMAC for codes and Argon2id for passphrases

A 100-bit random code cannot be brute-forced, so a fast keyed hash is safe and allows an indexed lookup. A passphrase is looked up by handle first, then verified, so a slow hash costs one computation per attempt and raises the price of guessing.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| Sequential or short numeric codes | Enumerable; violates the brief's non-guessable requirement. |
| Crockford mod-37 check symbol | Adds `*`, `~`, `$`, `=` symbols that are awkward on phone keyboards and in speech. |
| Argon2id for tracking codes | Prevents indexed lookup and gives no security gain over HMAC at 100 bits of entropy. |
| Plain SHA-256 of the code | Without a secret pepper, a database leak allows offline confirmation of a guessed code. |
| User-chosen handle or password | People reuse them and they can identify someone. |

## Consequences

- A code typed with `O` for `0` still works, and a single typo is caught before any database query.
- A database leak alone does not reveal or confirm tracking codes without the pepper.
- A lost code or passphrase cannot be recovered by anyone. The UI states this at display time.

## Migration impact

A new code length, alphabet, or checksum gets a new checksum version and coexists with version 1 until old reports close. Pepper rotation needs no data migration.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| Entropy, format, round trip, checksum | BE-062 | Property tests for 100-bit generation, typo detection, alias normalisation, and rejection of `U`. |
| Keyed storage only | BE-062 | Schema test asserts no raw-code column; log canary test on generation and lookup. |
| Generic lookup failure and rate limits | BE-065, BE-100 | Enumeration corpus with identical status, body, and headers for invalid, missing, and inaccessible codes. |
| Sealed idempotency replay | BE-034, BE-063 | Retry within the window returns the same code; stored row contains no raw code; replay after expiry returns the generic problem; mismatched fingerprint returns `409`. |
| Pepper rotation | BE-062 | Lookup under a retired pepper succeeds and rehashes to the active version. |
| Handle stores no identity | BE-066 | Schema introspection test for forbidden columns; generic failure and backoff tests. |
