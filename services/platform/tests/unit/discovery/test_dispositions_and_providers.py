"""The decision machine matches the contract; replay providers load and label fixtures honestly."""

import json
from itertools import product
from pathlib import Path

import pytest

from shaidago.discovery.dispositions import (
    COMMANDS,
    DECISIONS,
    DecisionNotAllowedError,
    find_decision,
)
from shaidago.discovery.fetcher import FetchError
from shaidago.discovery.pages import FixturePageFetcher
from shaidago.discovery.providers import build_providers, load_analysis_fixtures, replay_providers
from shaidago.shared.vocabulary import CONTRACT
from tests.factories import build_settings

MACHINE = json.loads(CONTRACT.read_text("utf-8"))["state_machines"]["discovered_source_disposition"]
STATES = ("not_reviewed", "attached", "rejected", "deferred")
ACTORS = ("reviewer", "admin", "reporter", "worker", "system")
ALLOWED = {
    (t["from"], t["command"], a): t["to"] for t in MACHINE["transitions"] for a in t["actors"]
}


def test_the_table_is_a_literal_copy_of_the_contract() -> None:
    assert [
        (d.from_state, d.command, d.to_state, sorted(d.actors), d.audit_event) for d in DECISIONS
    ] == [
        (t["from"], t["command"], t["to"], sorted(t["actors"]), t["audit_event"])
        for t in MACHINE["transitions"]
    ]


@pytest.mark.parametrize(("state", "command", "actor"), list(product(STATES, COMMANDS, ACTORS)))
def test_every_state_command_and_actor_matches_the_contract(
    state: str, command: str, actor: str
) -> None:
    expected = ALLOWED.get((state, command, actor))
    if expected is None:
        with pytest.raises(DecisionNotAllowedError):
            find_decision(state, command, actor)
    else:
        assert find_decision(state, command, actor).to_state == expected


async def test_recorded_pages_are_served_by_canonical_url_and_errors_replay(tmp_path: Path) -> None:
    path = tmp_path / "pages.json"
    path.write_text(
        json.dumps(
            {
                "fixture_version": 1,
                "pages": [
                    {
                        "url": "https://example.test/a/?utm_source=x",
                        "content_type": "text/html",
                        "body": "<p>Hello</p>",
                    },
                    {
                        "url": "https://example.test/gone",
                        "content_type": "text/html",
                        "body": "",
                        "error": "timeout",
                    },
                ],
            }
        ),
        "utf-8",
    )
    fetcher = FixturePageFetcher.from_file(path)
    page = await fetcher.fetch("https://example.test/a")
    assert (page.status, page.content_type, page.body) == (200, "text/html", b"<p>Hello</p>")
    for url, code in (
        ("https://example.test/gone", "timeout"),
        ("https://example.test/none", "fixture_missing"),
    ):
        with pytest.raises(FetchError) as raised:
            await fetcher.fetch(url)
        assert raised.value.code == code
    with pytest.raises(FetchError):
        await FixturePageFetcher.empty().fetch("https://example.test/a")
    for bad in ("nope", '{"fixture_version": 2, "pages": []}'):
        path.write_text(bad, "utf-8")
        with pytest.raises(FetchError):
            FixturePageFetcher.from_file(path)


def test_analysis_fixtures_load_or_are_absent(tmp_path: Path) -> None:
    assert load_analysis_fixtures(tmp_path / "missing.json") == {}
    path = tmp_path / "analysis.json"
    path.write_text(
        json.dumps(
            {
                "fixture_version": 1,
                "records": [{"fingerprint": "a" * 64, "output": {"summary": "x"}}],
            }
        ),
        "utf-8",
    )
    assert json.loads(load_analysis_fixtures(path)["a" * 64]) == {"summary": "x"}
    path.write_text(
        '{"fixture_version": 1, "records": [{"fingerprint": "bad", "output": {}}]}', "utf-8"
    )
    with pytest.raises(ValueError, match="invalid"):
        load_analysis_fixtures(path)


async def test_replay_mode_with_no_fixtures_finds_nothing_and_never_uses_the_network(
    tmp_path: Path,
) -> None:
    providers = replay_providers(tmp_path)
    results = await providers.search.search("Synthetic Clinic")
    assert (results.urls, results.demo_replay) == ((), True)
    assert providers.analyser_for("public") is providers.analyser_for("report")


def test_the_default_provider_mode_is_replay_and_live_needs_both_keys() -> None:
    assert build_providers(build_settings()) is not None  # replay is the development default
    from shaidago.shared.config import ConfigurationError  # noqa: PLC0415

    with pytest.raises(ConfigurationError):
        build_settings(PROVIDER_MODE="live")
