"""Apply a seed plan idempotently, and refuse unsafe targets.

Rows are found by natural key (locality slug, project slug, source URL, and so on). A row is
created if missing, updated only in fields the seed owns, and otherwise left alone, so a second
run changes nothing. The seed never touches reviewer-owned fields (a project's public status and
visibility, reviewed translations, any fact that is no longer a draft) and never rewrites or
deletes a source version: changed evidence becomes a new version and the old one stays.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.seed.plan import ALL_LOCALES, ProjectPlan, SeedPlan
from shaidago.shared.clock import Clock
from shaidago.shared.ids import IdGenerator

SAFE_ENVIRONMENTS = frozenset({"development", "test"})
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})
# Staging is the one deployed target that may hold demo data, and only when the operator asks for
# it by name. Production has no seed mode at all, with or without the flag.
DEPLOYED_SEED_ENVIRONMENT = "staging"
DEPLOYED_SEED_FLAG = "SEED_ALLOW_DEPLOYED"


class SeedRefusedError(Exception):
    """The seed will not run against this target. The message never includes credentials."""


def assert_safe_target(environ: Mapping[str, str], url: URL) -> None:
    """Demo seeding is for local development and test databases, or staging when asked by name.

    The staging path requires both ``APP_ENV=staging`` and ``SEED_ALLOW_DEPLOYED=1``, so no
    ordinary command, deploy hook, or typo can seed a deployed database. Production is refused
    whatever the flag says: there is no production seed mode.
    """
    app_env = environ.get("APP_ENV")
    if app_env == DEPLOYED_SEED_ENVIRONMENT:
        if environ.get(DEPLOYED_SEED_FLAG) != "1":
            raise SeedRefusedError(
                f"seeding {DEPLOYED_SEED_ENVIRONMENT} requires {DEPLOYED_SEED_FLAG}=1; "
                "it is never implied by the environment alone"
            )
        return  # the staging host is a private Railway address, so the local-host rule cannot apply
    if app_env not in SAFE_ENVIRONMENTS:
        raise SeedRefusedError(
            "the demo seed runs only when APP_ENV is development, test, or an explicitly "
            "flagged staging target; there is no production seed mode"
        )
    host = url.host or ""
    if host not in LOCAL_HOSTS and urlsplit(f"//{host}").hostname not in LOCAL_HOSTS:
        raise SeedRefusedError("the demo seed refuses a database that is not on the local machine")


@dataclass
class Counts:
    added: int = 0
    updated: int = 0
    unchanged: int = 0


@dataclass
class SeedReport:
    counts: dict[str, Counts] = field(default_factory=dict[str, Counts])
    gaps: list[str] = field(default_factory=list[str])

    def bump(self, entity: str, outcome: str) -> None:
        setattr(
            self.counts.setdefault(entity, Counts()),
            outcome,
            getattr(self.counts.get(entity, Counts()), outcome) + 1,
        )

    def render(self) -> str:
        lines = [f"{name:<13} added {c.added}, updated {c.updated}, unchanged {c.unchanged}"
                 for name, c in self.counts.items()]  # fmt: skip
        lines += ["", "Evidence gaps:", *(f"  - {gap}" for gap in self.gaps)]
        return "\n".join(lines) + "\n"


@dataclass
class Ctx:
    ids: IdGenerator
    now: Any
    report: SeedReport


async def _one(session: AsyncSession, sql: str, **params: Any) -> Any:
    return (await session.execute(text(sql), params)).one_or_none()


async def _run(session: AsyncSession, sql: str, **params: Any) -> None:
    await session.execute(text(sql), params)


async def _localities(s: AsyncSession, plan: SeedPlan, ctx: Ctx) -> dict[str, UUID]:
    found: dict[str, UUID] = {}
    for loc in plan.localities:
        parent = found.get(loc.parent_slug) if loc.parent_slug else None
        row = await _one(
            s, "SELECT id, name, kind, parent_id FROM app.localities WHERE slug = :s", s=loc.slug
        )
        if row is None:
            found[loc.slug] = ctx.ids.new()
            await _run(
                s,
                "INSERT INTO app.localities (id, slug, name, kind, parent_id, enabled_locales, "
                "created_at, updated_at) VALUES "
                "(:id, :slug, :name, :kind, :parent, :locales, :now, :now)",
                id=found[loc.slug], slug=loc.slug, name=loc.name, kind=loc.kind, parent=parent,
                locales=list(ALL_LOCALES), now=ctx.now,
            )  # fmt: skip
            ctx.report.bump("localities", "added")
            continue
        found[loc.slug] = row.id
        if (row.name, row.kind, row.parent_id) == (loc.name, loc.kind, parent):
            ctx.report.bump("localities", "unchanged")
        else:
            await _run(
                s,
                "UPDATE app.localities SET name = :n, kind = :k, parent_id = :p, updated_at = :now "
                "WHERE id = :id",
                n=loc.name, k=loc.kind, p=parent, now=ctx.now, id=row.id,
            )  # fmt: skip
            ctx.report.bump("localities", "updated")
    return found


async def _translations(
    s: AsyncSession,
    proj: ProjectPlan,
    project_id: UUID,
    ctx: Ctx,
) -> None:
    for tr in proj.translations:
        row = await _one(
            s,
            "SELECT id, title, summary, promised_deliverable, translation_status "
            "FROM app.project_translations WHERE project_id = :p AND locale = :l",
            p=project_id, l=tr.locale,
        )  # fmt: skip
        wanted = (tr.title, tr.summary, tr.promised_deliverable, tr.status)
        if row is None:
            await _run(
                s,
                "INSERT INTO app.project_translations (id, project_id, locale, title, summary, "
                "promised_deliverable, translation_status, created_at, updated_at) "
                "VALUES (:id, :p, :l, :t, :s, :d, :st, :now, :now)",
                id=ctx.ids.new(), p=project_id, l=tr.locale, t=tr.title, s=tr.summary,
                d=tr.promised_deliverable, st=tr.status, now=ctx.now,
            )  # fmt: skip
            ctx.report.bump("translations", "added")
        elif (
            row.translation_status == "reviewed"
            or (row.title, row.summary, row.promised_deliverable, row.translation_status) == wanted
        ):
            ctx.report.bump("translations", "unchanged")  # reviewed text is never overwritten
        else:
            await _run(
                s,
                "UPDATE app.project_translations SET title = :t, summary = :s, "
                "promised_deliverable = :d, translation_status = :st, updated_at = :now "
                "WHERE id = :id",
                t=tr.title, s=tr.summary, d=tr.promised_deliverable, st=tr.status,
                now=ctx.now, id=row.id,
            )  # fmt: skip
            ctx.report.bump("translations", "updated")


async def _projects(
    s: AsyncSession,
    plan: SeedPlan,
    locs: dict[str, UUID],
    ctx: Ctx,
) -> dict[str, UUID]:
    found: dict[str, UUID] = {}
    for proj in plan.projects:
        locality_id = locs[proj.locality_slug]
        row = await _one(
            s,
            "SELECT id, locality_id, category, last_checked_on FROM app.projects WHERE slug = :s",
            s=proj.slug,
        )
        wanted = (locality_id, proj.category, proj.checked_on)
        if row is None:
            found[proj.slug] = ctx.ids.new()
            # Status and visibility belong to reviewers: new rows start 'unknown', and a rerun
            # never changes them.
            await _run(
                s,
                "INSERT INTO app.projects (id, slug, locality_id, category, public_status, "
                "visibility, last_checked_on, created_at, updated_at) VALUES "
                "(:id, :slug, :loc, :cat, 'unknown', 'public', :checked, :now, :now)",
                id=found[proj.slug], slug=proj.slug, loc=locality_id, cat=proj.category,
                checked=proj.checked_on, now=ctx.now,
            )  # fmt: skip
            ctx.report.bump("projects", "added")
        else:
            found[proj.slug] = row.id
            if (row.locality_id, row.category, row.last_checked_on) == wanted:
                ctx.report.bump("projects", "unchanged")
            else:
                await _run(
                    s,
                    "UPDATE app.projects SET locality_id = :l, category = :c, "
                    "last_checked_on = :d, "
                    "updated_at = :now WHERE id = :id",
                    l=locality_id, c=proj.category, d=proj.checked_on, now=ctx.now, id=row.id,
                )  # fmt: skip
                ctx.report.bump("projects", "updated")
        await _translations(s, proj, found[proj.slug], ctx)
    return found


async def _sources(s: AsyncSession, plan: SeedPlan, ctx: Ctx) -> dict[str, UUID]:
    versions: dict[str, UUID] = {}
    for src in plan.sources:
        row = await _one(
            s,
            "SELECT id, title, publisher, availability FROM app.sources WHERE canonical_url = :u",
            u=src.url,
        )
        if row is None:
            source_id = ctx.ids.new()
            await _run(
                s,
                "INSERT INTO app.sources (id, canonical_url, title, publisher, source_type, "
                "information_class, availability, availability_checked_at, created_at, updated_at) "
                "VALUES (:id, :u, :t, :p, :st, :ic, :av, :chk, :now, :now)",
                id=source_id, u=src.url, t=src.title, p=src.publisher, st=src.source_type,
                ic=src.information_class, av=src.availability, chk=src.checked_at, now=ctx.now,
            )  # fmt: skip
            ctx.report.bump("sources", "added")
        else:
            source_id = row.id
            if (row.title, row.publisher, row.availability) == (
                src.title,
                src.publisher,
                src.availability,
            ):
                ctx.report.bump("sources", "unchanged")
            else:
                await _run(
                    s,
                    "UPDATE app.sources SET title = :t, publisher = :p, availability = :av, "
                    "availability_checked_at = :chk, updated_at = :now WHERE id = :id",
                    t=src.title, p=src.publisher, av=src.availability, chk=src.checked_at,
                    now=ctx.now, id=source_id,
                )  # fmt: skip
                ctx.report.bump("sources", "updated")
        # A version is content-addressed and immutable: unchanged evidence reuses it, changed
        # evidence adds a new one, and the old one is never edited or removed.
        version = await _one(
            s,
            "SELECT id FROM app.source_versions WHERE source_id = :s AND content_sha256 = :h",
            s=source_id, h=src.sha256,
        )  # fmt: skip
        if version is None:
            versions[src.url] = ctx.ids.new()
            await _run(
                s,
                "INSERT INTO app.source_versions (id, source_id, content_sha256, content_text, "
                "media_type, retrieved_at, review_state, created_at) VALUES "
                "(:id, :s, :h, :c, 'text/plain', :r, 'pending', :now)",
                id=versions[src.url], s=source_id, h=src.sha256, c=src.content,
                r=src.checked_at, now=ctx.now,
            )  # fmt: skip
            ctx.report.bump("versions", "added")
        else:
            versions[src.url] = version.id
            ctx.report.bump("versions", "unchanged")
    return versions


async def _facts(
    s: AsyncSession,
    plan: SeedPlan,
    projects: dict[str, UUID],
    versions: dict[str, UUID],
    ctx: Ctx,
) -> None:
    content = {src.url: src.content for src in plan.sources}
    checked = {p.slug: p.checked_on for p in plan.projects}
    for fact in plan.facts:
        row = await _one(
            s,
            "SELECT id, statement, visibility FROM app.project_facts "
            "WHERE project_id = :p AND kind = :k",
            p=projects[fact.project_slug], k=fact.kind,
        )  # fmt: skip
        if row is None:
            fact_id = ctx.ids.new()
            await _run(
                s,
                "INSERT INTO app.project_facts (id, project_id, kind, statement, effective_on, "
                "last_checked_on, verification_state, visibility, published_at, created_at, "
                "updated_at) VALUES (:id, :p, :k, :s, NULL, :chk, 'awaiting_verification', "
                "'draft', NULL, :now, :now)",
                id=fact_id, p=projects[fact.project_slug], k=fact.kind, s=fact.statement,
                chk=checked[fact.project_slug], now=ctx.now,
            )  # fmt: skip
            ctx.report.bump("facts", "added")
        else:
            fact_id = row.id
            if row.visibility == "draft" and row.statement != fact.statement:
                await _run(
                    s,
                    "UPDATE app.project_facts SET statement = :s, updated_at = :now WHERE id = :id",
                    s=fact.statement,
                    now=ctx.now,
                    id=fact_id,
                )
                ctx.report.bump("facts", "updated")
            else:
                ctx.report.bump("facts", "unchanged")
        for position, cite in enumerate(fact.citations, start=1):
            version_id = versions[cite.source_url]
            label = f"excerpt {position}"
            exists = await _one(
                s,
                "SELECT 1 FROM app.fact_citations WHERE fact_id = :f AND source_version_id = :v "
                "AND location_label = :l",
                f=fact_id, v=version_id, l=label,
            )  # fmt: skip
            if exists:
                ctx.report.bump("citations", "unchanged")
                continue
            await _run(
                s,
                "INSERT INTO app.fact_citations (id, fact_id, source_version_id, passage, "
                "location_label, passage_start, created_at) VALUES "
                "(:id, :f, :v, :p, :l, :start, :now)",
                id=ctx.ids.new(), f=fact_id, v=version_id, p=cite.passage, l=label,
                start=content[cite.source_url].index(cite.passage), now=ctx.now,
            )  # fmt: skip
            ctx.report.bump("citations", "added")


async def apply_plan(
    session: AsyncSession, plan: SeedPlan, *, clock: Clock, ids: IdGenerator
) -> SeedReport:
    report = SeedReport(gaps=list(plan.gaps))
    ctx = Ctx(ids=ids, now=clock.now(), report=report)
    localities = await _localities(session, plan, ctx)
    projects = await _projects(session, plan, localities, ctx)
    versions = await _sources(session, plan, ctx)
    await _facts(session, plan, projects, versions, ctx)
    return report
