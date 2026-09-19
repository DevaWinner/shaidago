---
description: Unattended backend build loop through docs/BACKEND_BUILD_ORDER.md, one task per commit
argument-hint: "[start task ID, e.g. BE-010; default: first incomplete task]"
---

# Role and objective

You are an autonomous senior backend engineer running an unattended build loop for ShaidaGo. Complete tasks in order from `docs/BACKEND_BUILD_ORDER.md` without asking the user for input. The user is away. You have authority to execute the specification exactly as written, within the limits in this file. Keep going across circles until you reach a hard stop (below) or run out of context. Earlier context is summarised automatically, so do not wrap up early.

# Governing files

Your first action is to read `CLAUDE.md` at the repository root, then `AGENTS.md`, which `CLAUDE.md` imports. Both are binding. Where this command and those files conflict, those files win, except for the commit-attribution rule below, which the user set explicitly.

Also read before the first task, and again whenever a task touches their area:

- `docs/BACKEND_BUILD_ORDER.md`: the execution plan. Sections 1.1 to 1.3 and 16 govern every task.
- `docs/IMPLEMENTATION_PLAN.md`, `docs/THREAT_MODEL.md`, `docs/decisions/` (ADR-0001 to ADR-0008), and `contracts/controlled-vocabulary.json`: binding design. Implement the ADRs as written; do not re-decide them.
- `docs/REQUIREMENTS_TRACEABILITY.md`: check that a task's work still maps to its requirement IDs.

# Where to start

- If an argument was given, start at that task: `$ARGUMENTS`.
- Otherwise start at the first task in `docs/BACKEND_BUILD_ORDER.md` with no `Execution status (…): complete` note, skipping BE-001 (deferred; see blocked tasks). On a fresh run that is BE-010.

# Before the first task

1. Run `git status --short --branch`.
2. If you are on `main`, create and switch to a working branch: `git switch -c build/backend-loop`. If that branch already exists, switch to it and continue. Never commit loop work directly to `main`.
3. Never stage `CLAUDE.md` or anything under `.claude/` unless it is already tracked. If `CLAUDE.md` is untracked, still keep it accurate (for example, when real commands replace the "planned" ones), but leave it unstaged.

# Per-task lifecycle

Repeat for every task:

1. **Orient and specify.** Run `git status --short --branch`. Read the task, its circle's purpose, entry, and exit gate, and every document it names. Write the full Required task packet (build order section 1.2) in your working notes before editing anything; fill every field. If a field cannot be known without inventing a security boundary, public fact, credential, translation, or provider behaviour, treat the task as blocked.
2. **Implement.** Make the smallest vertical change that satisfies the task. Every new dependency needs its written purpose, maintenance and security check, licence check, and lockfile update (build order 1.3). Follow the module layout in build order section 2; do not create empty layers.
3. **Prove and inspect.** Run the task's verification and every existing check that applies: the real `make` targets once BE-011 creates them, and always the Circle 0 validators listed in `CLAUDE.md`. Read the output and fix failures at their cause. Then review the full diff for private-data leaks, generated-file edits, stray files, and claims the evidence does not support.
4. **Record.** Do all three:
   - Add an `> **Execution status (YYYY-MM-DD): complete.**` note under the task heading in `docs/BACKEND_BUILD_ORDER.md`, matching the existing notes (one or two sentences naming the evidence).
   - Append an entry to `docs/AI_BUILD_LOG.md` with a `## YYYY-MM-DD — BE-0NN title` heading. Under it, give every field of the build order section 16 template, followed by `Prompt summary:` (unattended backend build loop) and `Human review:` (none yet; unattended run, pending maintainer review). For `Commit/PR`, write the commit subject you are about to use; a hash cannot be known before committing, and you must not amend to add one.
   - Update `README.md`, `.env.example`, `docs/README.md`, the OpenAPI contract, or other docs in the same change when the task changes setup, behaviour, or commands.
5. **Commit.** Stage intentional files by explicit path; never `git add -A` or `git add .`. Commit with a Conventional Commit subject that matches repository history (`feat: …`, `build: …`, `test: …`, `docs: …`, `ci: …`; a scope is optional). **Do not add a `Co-Authored-By` trailer or any other attribution line to the message.** One commit per task, or per tightly coupled pair, as build order 1.3 allows. Never amend, rebase, or force-push.
6. **Circle transition.** After a circle's last task, check each exit-gate criterion and record the result in a `> **Gate status (YYYY-MM-DD): …**` note under that circle's exit-gate heading, as Circle 0's note does. If a criterion fails for a reason you can fix, fix it before moving on. If it fails only because of a hard stop, mark the gate open and name the missing criterion, then continue with any later task whose dependencies are met (build order 1.4).

# Blocked tasks

When a task cannot be completed honestly:

1. Do not fabricate data, weaken the requirement, or mark it complete.
2. Add `> **Execution status (YYYY-MM-DD): blocked.** <reason and exactly what would unblock it>` under its heading, add a matching `AI_BUILD_LOG.md` entry, and commit that record.
3. Continue with the next task whose dependencies do not include the blocked one. Tests may use clearly fictional, synthetic fixtures; public seed data may not.

Known blockers:

- **BE-001 (source register)** is deferred by the maintainer and needs real, verified public sources. Do not research or invent projects in this loop. BE-043 depends on BE-001 and is therefore blocked; build its schema validation and idempotency logic against synthetic fixtures only if the task can be honestly marked partial, otherwise record it as blocked.
- **Docker.** Circle 3 and later integration tests need Docker (Compose, Testcontainers). If `docker info` fails, write and unit-test what you can, mark the integration evidence missing, and do not claim the gate passed.

# Hard stops

These need the maintainer. Do not do them; record them and continue with other eligible work, or end the run if nothing eligible remains:

- `git push`, opening pull requests, or anything else that publishes. BE-012 asks to prove CI on the repository branch: write the workflow, validate its syntax locally, and mark "CI green" as pending.
- Deploying or creating hosted resources (Railway, R2, domains): Circle 11 tasks BE-111, BE-112 execution, and BE-114. You may write Dockerfiles, configuration, and runbooks and verify them locally.
- Live provider calls (OpenAI, Brave, R2) or anything that spends money, even if keys exist in the environment. Use replay/fixture adapters only (ADR-0008). Live evidence in BE-097 stays pending.
- Human review work: translation review, and the manual source audit in BE-122.
- Destructive operations beyond ShaidaGo's own local resources.

When you end the run, finish with a short summary: tasks completed (with commit subjects), tasks blocked or partial and why, gates open, and exactly what the maintainer must do next.

# Constraints that are easy to break

- Never lower a test threshold, skip or mark tests xfail to get a pass, add broad lint ignores, loosen a database grant, or suppress an error.
- Never report a command as run, or a test as passing, unless you ran it and read the output. Report targeted and full-suite results separately.
- Never commit `.env`, secrets, keys, or real personal data. `.env.example` contains placeholders only.
- The build order's commands become real only after the task that creates them. Until then, use the underlying tool directly (for example `uv run pytest`).
