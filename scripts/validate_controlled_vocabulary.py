#!/usr/bin/env python3
"""Validate ShaidaGo's controlled vocabulary contract without dependencies."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "contracts" / "controlled-vocabulary.json"
MACHINE_VALUE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
REQUIRED_VOCABULARIES = {
    "project_category",
    "project_public_status",
    "information_class",
    "source_type",
    "source_review_state",
    "source_availability",
    "verification_state",
    "report_concern_category",
    "report_risk_level",
    "report_status",
    "evidence_sanitation_state",
    "malware_scan_state",
    "discovery_status",
    "discovered_source_disposition",
    "translation_status",
}
REQUIRED_STATE_MACHINES = {
    "project_public_status",
    "source_review_state",
    "source_availability",
    "verification_state",
    "report_risk_level",
    "report_status",
    "evidence_sanitation_state",
    "malware_scan_state",
    "discovery_status",
    "discovered_source_disposition",
    "translation_status",
}
TRANSITION_FIELDS = {
    "from",
    "command",
    "actors",
    "to",
    "audit_event",
    "public_visibility",
}


class ContractError(ValueError):
    """Raised when the vocabulary contract violates a deterministic rule."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def require_machine_value(value: Any, location: str) -> str:
    require(isinstance(value, str), f"{location} must be a string")
    require(bool(MACHINE_VALUE.fullmatch(value)), f"{location} is not lowercase snake-case: {value!r}")
    return value


def load_contract(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContractError(f"contract does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ContractError(f"invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}") from error
    require(isinstance(data, dict), "contract root must be an object")
    return data


def validate_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schema_version") == 1, "schema_version must be 1")
    require(contract.get("contract_id") == "shaidago-controlled-vocabulary", "unexpected contract_id")
    require(contract.get("machine_value_pattern") == MACHINE_VALUE.pattern, "machine value pattern drifted")

    actors = contract.get("actors")
    require(isinstance(actors, list) and actors, "actors must be a non-empty array")
    actor_values = [require_machine_value(actor, "actors[]") for actor in actors]
    require(len(actor_values) == len(set(actor_values)), "actors must be unique")
    actor_set = set(actor_values)

    vocabularies = contract.get("vocabularies")
    require(isinstance(vocabularies, dict), "vocabularies must be an object")
    require(set(vocabularies) == REQUIRED_VOCABULARIES, "required vocabulary set is incomplete or contains an unreviewed field")

    states_by_vocabulary: dict[str, set[str]] = {}
    for name, definition in vocabularies.items():
        require_machine_value(name, f"vocabularies.{name}")
        require(isinstance(definition, dict), f"vocabularies.{name} must be an object")
        require(definition.get("kind") in {"classification", "state"}, f"vocabularies.{name}.kind is invalid")
        require(isinstance(definition.get("change_policy"), str) and definition["change_policy"], f"vocabularies.{name}.change_policy is required")

        values = definition.get("values")
        require(isinstance(values, list) and values, f"vocabularies.{name}.values must be non-empty")
        seen_values: set[str] = set()
        seen_meanings: set[str] = set()
        for index, item in enumerate(values):
            location = f"vocabularies.{name}.values[{index}]"
            require(isinstance(item, dict), f"{location} must be an object")
            value = require_machine_value(item.get("value"), f"{location}.value")
            meaning = item.get("meaning")
            require(isinstance(meaning, str) and meaning.strip(), f"{location}.meaning is required")
            require(value not in seen_values, f"vocabularies.{name} repeats value {value!r}")
            require(meaning not in seen_meanings, f"vocabularies.{name} reuses one meaning for multiple values")
            seen_values.add(value)
            seen_meanings.add(meaning)
        states_by_vocabulary[name] = seen_values

        if definition["kind"] == "state":
            initial_state = definition.get("initial_state")
            require(initial_state in seen_values, f"vocabularies.{name}.initial_state must name a declared state")
            terminal_states = definition.get("terminal_states")
            require(isinstance(terminal_states, list), f"vocabularies.{name}.terminal_states must be an array")
            require(set(terminal_states) <= seen_values, f"vocabularies.{name} has an unknown terminal state")
            quiescent_states = definition.get("quiescent_states", [])
            require(isinstance(quiescent_states, list), f"vocabularies.{name}.quiescent_states must be an array")
            require(set(quiescent_states) <= seen_values, f"vocabularies.{name} has an unknown quiescent state")
        else:
            require("initial_state" not in definition, f"classification {name} must not declare an initial state")
            require("terminal_states" not in definition, f"classification {name} must not declare terminal states")

    state_machines = contract.get("state_machines")
    require(isinstance(state_machines, dict), "state_machines must be an object")
    require(set(state_machines) == REQUIRED_STATE_MACHINES, "required state-machine set is incomplete or contains an unreviewed machine")

    seen_failure_codes: set[str] = set()
    for name, machine in state_machines.items():
        require(vocabularies[name]["kind"] == "state", f"state machine {name} must reference a state vocabulary")
        require(isinstance(machine, dict), f"state_machines.{name} must be an object")
        failure_code = require_machine_value(machine.get("failure_code"), f"state_machines.{name}.failure_code")
        require(failure_code not in seen_failure_codes, f"failure code {failure_code!r} is reused")
        seen_failure_codes.add(failure_code)

        transitions = machine.get("transitions")
        require(isinstance(transitions, list) and transitions, f"state_machines.{name}.transitions must be non-empty")
        known_states = states_by_vocabulary[name]
        terminal_states = set(vocabularies[name]["terminal_states"])
        seen_transition_keys: set[tuple[str, str]] = set()
        referenced_states: set[str] = set()

        for index, transition in enumerate(transitions):
            location = f"state_machines.{name}.transitions[{index}]"
            require(isinstance(transition, dict), f"{location} must be an object")
            require(set(transition) == TRANSITION_FIELDS, f"{location} must contain exactly {sorted(TRANSITION_FIELDS)}")
            current = require_machine_value(transition["from"], f"{location}.from")
            command = require_machine_value(transition["command"], f"{location}.command")
            target = require_machine_value(transition["to"], f"{location}.to")
            require_machine_value(transition["audit_event"], f"{location}.audit_event")
            require_machine_value(transition["public_visibility"], f"{location}.public_visibility")
            require(current in known_states, f"{location}.from references unknown state {current!r}")
            require(target in known_states, f"{location}.to references unknown state {target!r}")
            require(current != target, f"{location} must change state")
            require(current not in terminal_states, f"{location} leaves terminal state {current!r}")

            transition_actors = transition["actors"]
            require(isinstance(transition_actors, list) and transition_actors, f"{location}.actors must be non-empty")
            require(len(transition_actors) == len(set(transition_actors)), f"{location}.actors contains duplicates")
            require(set(transition_actors) <= actor_set, f"{location}.actors contains an unknown actor")

            key = (current, command)
            require(key not in seen_transition_keys, f"state machine {name} has ambiguous transition {key}")
            seen_transition_keys.add(key)
            referenced_states.update({current, target})

        require(referenced_states == known_states, f"state machine {name} does not reference every declared state")


def run_negative_self_tests(contract: dict[str, Any]) -> None:
    mutations: list[tuple[str, dict[str, Any]]] = []

    invalid_case = copy.deepcopy(contract)
    invalid_case["vocabularies"]["project_category"]["values"][0]["value"] = "Health"
    mutations.append(("uppercase machine value", invalid_case))

    unknown_target = copy.deepcopy(contract)
    unknown_target["state_machines"]["report_status"]["transitions"][0]["to"] = "invented_state"
    mutations.append(("unknown transition target", unknown_target))

    terminal_escape = copy.deepcopy(contract)
    terminal_escape["state_machines"]["discovery_status"]["transitions"].append(
        {
            "from": "complete",
            "command": "restart",
            "actors": ["worker"],
            "to": "queued",
            "audit_event": "discovery_restarted",
            "public_visibility": "scope_safe_progress",
        }
    )
    mutations.append(("transition from terminal state", terminal_escape))

    for name, mutation in mutations:
        try:
            validate_contract(mutation)
        except ContractError:
            continue
        raise ContractError(f"negative self-test did not reject {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--self-test", action="store_true", help="also run deterministic negative tests")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        contract = load_contract(args.path)
        validate_contract(contract)
        if args.self_test:
            run_negative_self_tests(contract)
    except ContractError as error:
        print(f"controlled vocabulary: FAIL: {error}", file=sys.stderr)
        return 1

    suffix = " with negative self-tests" if args.self_test else ""
    print(f"controlled vocabulary: OK{suffix} ({args.path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
