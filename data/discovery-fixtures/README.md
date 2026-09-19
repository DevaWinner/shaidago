# Discovery replay fixtures

Synthetic inputs for the Source Scout replay providers (ADR-0008). They describe a fictional
"Fixture Scenario" project on reserved `.test` domains; nothing here is a real page, publisher,
project, or person, and no replay result may be presented as a live one.

`search.json`, `pages.json`, `analysis.json`, and `scenarios.json` are generated. Change a scenario
in `services/platform/scripts/build_discovery_fixtures.py`, then run
`uv run python scripts/build_discovery_fixtures.py` from `services/platform`; the test suite fails
if a committed file drifts from the generator.
