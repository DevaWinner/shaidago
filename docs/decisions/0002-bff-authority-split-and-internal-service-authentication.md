# ADR-0002: BFF/private API authority split and internal-service authentication

- **Status:** accepted
- **Date:** 2026-09-19
- **Task:** BE-004
- **Supersedes:** none

## Context

Browsers call only the Next.js origin. Next.js Server Components and Route Handlers call FastAPI over Railway private networking. The threat model (`docs/THREAT_MODEL.md`, TB-02 and TM-S03) requires that a private hostname alone is not authentication: a misrouted request, a compromised neighbouring service, or a future network change must not grant access to report operations. The BFF also forwards context the API needs, such as request ID, locale, and a rotating HMAC of the client IP for rate limiting, and the API must know that context came from a trusted caller.

Uploads stream through the BFF to the API, so any mechanism that hashes the full body before forwarding would force buffering.

## Decision

### Authority split

1. FastAPI is the only authority for validation of domain rules, authorisation, visibility, encryption, state transitions, citations, audit, and publication.
2. The BFF owns browser concerns only: same-origin cookies, Origin and CSRF checks, body-size limits, locale propagation, request IDs, and browser-safe error shaping. It never decides whether a reviewer may act, a report is visible, or evidence is verified.
3. The BFF may reject a request early (size, origin, CSRF), but the API re-checks everything it relies on.

### Internal-service authentication

1. Each internal caller has an identity. The pilot has one: `web` (the Next.js server). The worker does not call the API (ADR-0001).
2. Each identity has a 256-bit random bearer credential, sent as `Authorization: Bearer <caller-id>.<secret>` on every BFF-to-API request.
3. The API stores up to two accepted secrets per caller, `current` and `previous`, from environment secrets, and compares with a constant-time comparison. Rotation: add a new `current`, move the old one to `previous`, redeploy the web service, then remove `previous`.
4. Verification runs as the first middleware before any router, including `/v1` public routes. Only `/health/live` is exempt. A failed check returns the generic `401` problem response and a security log event with the caller ID only.
5. Forwarded context headers (`X-Request-Id`, `X-Shaidago-Locale`, `X-Shaidago-Client-Hmac`) are read only after caller authentication succeeds. They are syntax-validated; an invalid value is replaced (request ID) or ignored (locale, client HMAC), never trusted.
6. The credential is server-only in Next.js: read from `process.env` in server modules marked `server-only`, never in `NEXT_PUBLIC_*` variables, logs, or client bundles.
7. Reviewer sessions (BE-051) and tracking or handle credentials (ADR-0005) are separate. Possessing the internal credential never grants reviewer authority.

## Alternatives considered

| Alternative | Reason rejected |
| --- | --- |
| Trust the private network | Rejected by the threat model; one routing or configuration mistake exposes every private route. |
| HMAC request signing over method, path, timestamp, and body hash | Body hashing conflicts with streamed uploads, and clock-skew handling adds failure modes. Bearer credentials over the private network give the same caller authentication for this topology. |
| Mutual TLS | Railway provides no managed internal certificate authority; issuing and rotating certificates by hand costs more than it protects for one caller. |
| Short-lived signed JWTs from the BFF | Adds a signing key, clock dependency, and token parsing surface without a second caller or delegated claims to justify it. |

## Consequences

- A request from an unauthenticated network neighbour reaches no route handler.
- Rotation is a two-step deploy with no downtime.
- A leaked web credential lets an attacker act as the BFF, but not as a reviewer or reporter: every private action still needs a session or tracking credential. Rotation is the containment step (BE-113 runbook).
- If a second caller appears, it gets its own identity and permission set rather than sharing `web`.

## Migration impact

Moving to mTLS or signed requests later changes only the middleware and the BFF client wrapper; routes and domain code are unaffected.

## Enforcement

| Control | Owning task | Planned verification |
| --- | --- | --- |
| Caller authentication before every router | BE-022 | Tests for missing, malformed, wrong-caller, rotated `previous`, removed, and valid credentials. |
| Constant-time comparison and generic denial | BE-022 | Unit test asserts the comparison function and an identical problem body for every failure. |
| Forwarded context trusted only after authentication | BE-023 | Test sends forged context headers without a credential and asserts they are ignored. |
| Credential absent from client bundles and logs | BE-023, FE-116 | Log canary test; build-output scan for the credential variable name and canary value. |
| Internal credential is not reviewer authority | BE-052, BE-053 | Reviewer routes called with a valid internal credential and no session are denied. |
