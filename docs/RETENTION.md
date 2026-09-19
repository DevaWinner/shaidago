# Retention, deletion, and operational privacy (prototype)

These are the technical controls that exist and the ones that do not. **Nothing here is a claim of compliance with the Nigeria Data Protection Act, GDPR, or any whistleblower law.** The production gate stays closed until legal, privacy, and operational review sets real periods, lawful bases, and processes. The prototype handles only fictional reports.

| Data | Prototype behaviour | Mechanism | Limitation |
| --- | --- | --- | --- |
| Reviewer sessions | Expire by idle and absolute time; deleted 7 days after expiry or revocation | `make retention-purge` | Someone must schedule the command (the Railway runbook in BE-113 names a cron service). |
| Idempotency records | Expire by design; expired rows deleted | `make retention-purge` | As above. |
| Rate-limit state | Redis keys expire with their window | Redis TTL | None beyond Redis availability. |
| Upload scratch files | The raw upload is deleted on every path within the request; crash leftovers (`sg-upload-*`) older than an hour are removed | `make retention-purge` | The sweep covers the process's temporary directory only. |
| Reports, contacts, evidence, notes, follow-up answers, decision reasons | **Not aged out automatically.** An operator can make one report's private content permanently unreadable (`python -m shaidago.retention shred-report <id>`) or shred all closed reports closed more than N days ago (`shred-closed <days>`). Shredding destroys every data key that protects the content, clears the contact ciphertext, and deletes the evidence objects and rows. | Crypto-shredding | The retention period is a decision this repository does not make. Report-scoped discovery runs and their public-page excerpts are kept (they hold no private text; their decision reasons are shredded). |
| Status history and audit events | Append-only and kept: they hold identifiers, commands, and states, never report text, contacts, or tracking codes | Database triggers | No purge exists on purpose. A retention period for audit data needs a decision. |
| Reporter handles | Deletion unlinks every report and removes the credential | `POST /v1/reporter-handles:delete` | Reports stay, anonymous. |
| Published updates | Separate public data; shredding a report does not touch them | Design | A published update is a public record; withdrawing one is a separate decision. |
| Provider and replay data | Replay fixtures are synthetic. Live calls send only allowlisted public text with `store: false`; questions are not stored (only metrics); discovery keeps a short excerpt of a public page. | Provider interface | Provider-side retention depends on the account's terms, which are not verified here. |
| Backups | **Not configured or verified.** Backups hold ciphertext and the wrapped keys as they were when taken. | None yet | Restoring an older backup resurrects keys shredded since. After any restore, re-shred every report that has a `report_shredded` audit event (`SELECT subject_id FROM app.audit_events WHERE event = 'report_shredded'`). Backup retention should be shorter than any deletion commitment. |
| Encryption keys | KEKs are versioned; `make kek-rotate` rewraps data keys | `docs/KEY_MANAGEMENT.md` | Rotation is manual. |
| Reviewer access | `python -m shaidago.retention review-reviewers <days>` lists active reviewers with no recent sign-in; a credential change or disable revokes their sessions | Operator review | The review is a manual, periodic act; no schedule is enforced. |

Shredding is irreversible. It is safe to repeat, and it is written to the audit log with counts only.
