#!/usr/bin/env python3
"""Render docs/SOURCE_REGISTER.md from data/source-register.json.  Use --check to detect drift."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "source-register.json"
DOC = ROOT / "docs" / "SOURCE_REGISTER.md"

NOT_A_CONCLUSION = (
    "Nothing here is a finding about any person or organisation. A fact is what one named source "
    "says, at the recorded date."
)


def render(reg: dict) -> str:  # noqa: C901
    sources = {s["id"]: s for s in reg["sources"]}
    out = [
        "# Source register",
        "",
        "<!-- Generated from data/source-register.json by scripts/render_source_register.py. "
        "Edit the JSON, not this file. -->",
        "",
        f"- **Prepared:** {reg['prepared_on']}",
        f"- **Scope:** {reg['scope']}",
        "- **Machine-readable register:** [`data/source-register.json`](../data/source-register.json), "
        "checked by `python3 scripts/validate_source_register.py --self-test`.",
        "",
        "This is the evidence baseline for the six seed projects. " + NOT_A_CONCLUSION,
        "",
        "## Method",
        "",
        reg["method"],
        "",
        "Source availability is recorded on each source and is separate from whether a fact is verified. "
        "All incident reports are fictional and labelled.",
        "",
        "## Summary",
        "",
        "| Project | Sources read | Facts with an exact verified passage | Facts not verified |",
        "| --- | --- | --- | --- |",
    ]
    for project in reg["projects"]:
        ids = {r["source_id"] for f in project["facts"] for r in f["sources"]}
        ok = sum(f["evidence_status"] == "exact_passage_verified" for f in project["facts"])
        bad = len(project["facts"]) - ok
        readable = sum(sources[i]["availability"] == "available" for i in ids)
        out.append(f"| {project['id']} {project['title']} | {readable} of {len(ids)} | {ok} | {bad} |")
    out += ["", "## Sources", "", "| ID | Publisher | Published | Retrieved | Availability | Page hash (SHA-256 of bytes received) |", "| --- | --- | --- | --- | --- | --- |"]
    for s in reg["sources"]:
        digest = f"`{s['raw_page_sha256']}`" if s["raw_page_sha256"] else "none (not retrieved)"
        out.append(f"| {s['id']} | {s['publisher']} | {s['published_on'] or 'unknown'} | {s['retrieved_on']} | {s['availability']} | {digest} |")
    out += ["", "Each source's URL, retrieval method and reuse constraints:", ""]
    for s in reg["sources"]:
        out += [f"- **{s['id']}** {s['url']}", f"  - Retrieval: {s['retrieval']}", f"  - Reuse: {s['reuse_constraints']}"]
    for project in reg["projects"]:
        out += ["", f"## {project['id']}: {project['title']}", "", f"- **Locality:** {project['locality']}  ", f"- **Category:** {project['category']}  ", f"- **Proposed public status:** {project['proposed_public_status']} ({project['status_basis']})  ", f"- **Last checked:** {project['last_checked_on']}"]
        for fact in project["facts"]:
            out += ["", f"### {fact['id']}", "", f"- **Statement:** {fact['statement']}", f"- **Evidence:** {fact['evidence_status']}; proposed verification state `{fact['proposed_verification_state']}`; seed eligibility `{fact['seed_eligibility']}`"]
            if fact["note"]:
                out.append(f"- **Note:** {fact['note']}")
            for ref in fact["sources"]:
                out.append(f"- **Source:** {ref['source_id']}")
                for p in ref["passages"]:
                    out.append(f"  - Exact passage: \"{p['text']}\" (`{p['sha256'][:16]}...`)")
                if ref.get("claimed_passage_not_verified"):
                    out.append(f"  - Claimed but **not verified**: \"{ref['claimed_passage_not_verified']}\"")
        out += ["", "**Unresolved gaps**", ""] + [f"- {g}" for g in project["unresolved_gaps"]]
        for report in project["fictional_reports"]:
            out += ["", f"**[{report['label']}]** *[DEMO ONLY]* {report['text']}", f"*Maintainer decision needed:* {report['maintainer_review']}"]
    out += ["", "## Escalation guidance (not verified)", "", "None of these has a cited source, verification date, or instructions, so none can be seeded (BE-042). No contact detail is recorded.", "", "| Organisation | Purpose stated in the submitted draft | Status |", "| --- | --- | --- |"]
    for r in reg["escalation_routes"]:
        out.append(f"| {r['organisation']} | {r['claimed_purpose']} | {r['status']} |")
    out += ["", "## Locale text and translation labels", "", "BWARI-01 summary. No fluent reviewer is recorded for any of these, so every one is `machine_assisted`.", ""]
    for t in reg["translations"]:
        out += [f"- **{t['locale']}** (`{t['translation_status']}`): {t['text']}", f"  - {t['note']}"]
    return "\n".join(out) + "\n"


def main() -> int:
    rendered = render(json.loads(DATA.read_text(encoding="utf-8")))
    if "--check" in sys.argv:
        if not DOC.exists() or DOC.read_text(encoding="utf-8") != rendered:
            sys.stderr.write("docs/SOURCE_REGISTER.md is out of date; run scripts/render_source_register.py\n")
            return 1
        sys.stdout.write("source register render: OK\n")
        return 0
    DOC.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
