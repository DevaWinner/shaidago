import inspect
from uuid import uuid4

import pytest

from shaidago.auth.policy import POLICY, Capability, authorize, is_allowed
from shaidago.auth.sessions import Principal
from shaidago.shared.problems import FORBIDDEN, ProblemError

ADMIN_ONLY = {Capability.SOURCE_REOPEN_SUPERSEDED, Capability.REVIEWER_ADMIN}
EVERYONE = set(Capability) - ADMIN_ONLY


def principal(role: str) -> Principal:
    return Principal(uuid4(), "someone", role, uuid4())  # type: ignore[arg-type]


def test_every_capability_has_an_explicit_entry() -> None:
    assert set(POLICY) == set(Capability)


@pytest.mark.parametrize("capability", sorted(EVERYONE))
def test_reviewers_and_admins_hold_the_operational_capabilities(capability: Capability) -> None:
    assert is_allowed("reviewer", capability)
    assert is_allowed("admin", capability)


@pytest.mark.parametrize("capability", sorted(ADMIN_ONLY))
def test_only_admins_hold_the_administrative_capabilities(capability: Capability) -> None:
    assert is_allowed("admin", capability)
    assert not is_allowed("reviewer", capability)
    with pytest.raises(ProblemError) as raised:
        authorize(principal("reviewer"), capability)
    assert raised.value.problem is FORBIDDEN


@pytest.mark.parametrize("role", ["", "reporter", "system", "worker", "root", "ADMIN", "Reviewer"])
@pytest.mark.parametrize("capability", sorted(Capability))
def test_unknown_or_non_reviewer_roles_have_no_capability(
    role: str, capability: Capability
) -> None:
    assert not is_allowed(role, capability)
    with pytest.raises(ProblemError):
        authorize(principal(role), capability)


def test_a_denial_is_identical_for_every_capability_and_carries_no_detail() -> None:
    problems: set[tuple[object, ...]] = set()
    for capability in Capability:
        try:
            authorize(principal("reporter"), capability)
        except ProblemError as error:
            problems.add((error.problem, error.field_errors, tuple(error.headers.items())))
    assert problems == {(FORBIDDEN, (), ())}


def test_policy_functions_take_no_http_or_record_arguments() -> None:
    assert list(inspect.signature(authorize).parameters) == ["principal", "capability"]
    assert list(inspect.signature(is_allowed).parameters) == ["role", "capability"]
