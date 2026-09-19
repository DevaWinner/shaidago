"""Turn the validated source register into a database-independent seed plan.

Only facts whose passage was verified word for word are planned. Nothing is published: source
versions stay ``pending`` and facts stay drafts, because approving evidence and publishing a fact
are separate human acts. A project with no verified fact, and no text to show, is not planned and is
reported as an evidence gap instead. Public status stays ``unknown`` until a reviewer approves a
citation for a status claim.
"""

import hashlib
import importlib.util
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[5]
REGISTER_PATH = REPOSITORY / "data" / "source-register.json"
_VALIDATOR = REPOSITORY / "scripts" / "validate_source_register.py"

FCT = ("fct-abuja", "Federal Capital Territory (Abuja)", "state", None)
LOCALITIES = {
    "AMAC": ("amac", "Abuja Municipal Area Council (AMAC)", "area_council", "fct-abuja"),
    "Bwari": ("bwari", "Bwari Area Council", "area_council", "fct-abuja"),
}
ALL_LOCALES = ("en", "ha", "ig", "yo")


class RegisterInvalidError(ValueError):
    """The register failed validation; nothing may be written."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("source register is invalid: " + "; ".join(problems))


def _validator() -> Any:
    spec = importlib.util.spec_from_file_location("validate_source_register", _VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("the register validator is missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_register(path: Path = REGISTER_PATH) -> dict[str, Any]:
    """Read and validate the register. Raises ``RegisterInvalidError`` before anything else runs."""
    register: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = _validator().check(register)
    if problems:
        raise RegisterInvalidError(problems)
    return register


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@dataclass(frozen=True)
class LocalityPlan:
    slug: str
    name: str
    kind: str
    parent_slug: str | None


@dataclass(frozen=True)
class TranslationPlan:
    locale: str
    title: str
    summary: str
    promised_deliverable: str
    status: str


@dataclass(frozen=True)
class ProjectPlan:
    slug: str
    locality_slug: str
    category: str
    checked_on: date
    translations: tuple[TranslationPlan, ...]


@dataclass(frozen=True)
class SourcePlan:
    url: str
    title: str
    publisher: str
    source_type: str
    information_class: str
    availability: str
    checked_at: datetime
    content: str  # the cited excerpts only, never the full page

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()


@dataclass(frozen=True)
class CitationPlan:
    source_url: str
    passage: str


@dataclass(frozen=True)
class FactPlan:
    project_slug: str
    kind: str
    statement: str
    citations: tuple[CitationPlan, ...]


@dataclass
class SeedPlan:
    localities: list[LocalityPlan] = field(default_factory=list[LocalityPlan])
    projects: list[ProjectPlan] = field(default_factory=list[ProjectPlan])
    sources: list[SourcePlan] = field(default_factory=list[SourcePlan])
    facts: list[FactPlan] = field(default_factory=list[FactPlan])
    gaps: list[str] = field(default_factory=list[str])


def build_plan(register: dict[str, Any]) -> SeedPlan:
    plan = SeedPlan()
    by_id = {s["id"]: s for s in register["sources"]}
    excerpts: dict[str, list[str]] = {}
    translations = {(t["project_id"], t["locale"]): t for t in register["translations"]}
    used_localities: set[str] = set()
    for project in register["projects"]:
        eligible = [
            f for f in project["facts"] if f["seed_eligibility"] == "eligible_as_cited_draft"
        ]
        skipped = len(project["facts"]) - len(eligible)
        if not eligible:
            plan.gaps.append(
                f"{project['id']}: not seeded, no fact with a verified passage "
                f"({skipped} unverified; see docs/SOURCE_REGISTER.md)"
            )
            continue
        slug = slugify(project["title"])
        locality = LOCALITIES[project["locality"]]
        used_localities.add(project["locality"])
        title = project["title"]
        texts: list[TranslationPlan] = []
        supplied = [translations.get((project["id"], loc)) for loc in ALL_LOCALES]
        if all(supplied):
            texts = [
                TranslationPlan(t["locale"], title, t["text"], "", t["translation_status"])
                for t in supplied
                if t
            ]
        else:
            # No summary was supplied, so the summary is the first verified statement.
            texts = [TranslationPlan("en", title, eligible[0]["statement"], "", "machine_assisted")]
        plan.projects.append(
            ProjectPlan(
                slug,
                locality[0],
                project["category"],
                date.fromisoformat(project["last_checked_on"]),
                tuple(texts),
            )
        )
        if project["proposed_public_status"] != "unknown":
            plan.gaps.append(
                f"{project['id']}: proposed status '{project['proposed_public_status']}' is held "
                "at 'unknown' until a reviewer approves a citation for it"
            )
        if skipped:
            plan.gaps.append(f"{project['id']}: {skipped} unverified fact(s) not seeded")
        for fact in eligible:
            cites: list[CitationPlan] = []
            for ref in fact["sources"]:
                passages = [p["text"] for p in ref["passages"]]
                excerpts.setdefault(ref["source_id"], []).extend(passages)
                cites.extend(
                    CitationPlan(by_id[ref["source_id"]]["url"], text) for text in passages
                )
            kind = fact["id"].lower().replace("-", "_")
            plan.facts.append(FactPlan(slug, kind, fact["statement"], tuple(cites)))
    for code in sorted(used_localities):
        slug, name, kind, parent = LOCALITIES[code]
        plan.localities.append(LocalityPlan(slug, name, kind, parent))
    if plan.localities:
        plan.localities.insert(0, LocalityPlan(*FCT))
    for sid in sorted(excerpts):
        source = by_id[sid]
        unique = sorted(set(excerpts[sid]))
        checked = datetime.fromisoformat(source["retrieved_on"]).replace(hour=12, tzinfo=UTC)
        plan.sources.append(
            SourcePlan(
                source["url"], source["title"], source["publisher"], source["source_type"],
                source["information_class"], source["availability"], checked, "\n\n".join(unique),
            )
        )  # fmt: skip
    plan.gaps.append("escalation routes: none seeded; no route has a source, date, or instructions")
    plan.gaps.append(
        "fictional report fixtures: not seeded; the private report tables do not exist yet"
    )
    return plan
