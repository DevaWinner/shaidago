from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError

from shaidago.shared.database import sqlstate, translate_database_error
from shaidago.shared.problems import CONFLICT


class FakeDriverError(Exception):
    def __init__(self, state: str | None) -> None:
        super().__init__("driver detail that must never surface")
        self.sqlstate = state


def wrapped(cls: type[DBAPIError], state: str | None) -> DBAPIError:
    return cls("SELECT 1", {}, FakeDriverError(state))


def test_unique_serialization_and_deadlock_outcomes_become_conflicts() -> None:
    for state, cls in (
        ("23505", IntegrityError),
        ("40001", OperationalError),
        ("40P01", OperationalError),
    ):
        problem = translate_database_error(wrapped(cls, state))
        assert problem is not None
        assert problem.problem is CONFLICT


def test_other_integrity_and_unknown_errors_stay_internal() -> None:
    for state in ("23503", "23502", "23514", "42P01", "57014", "XX000", None):
        assert translate_database_error(wrapped(DBAPIError, state)) is None


def test_sqlstate_is_none_without_a_driver_error() -> None:
    assert sqlstate(ValueError("no orig")) is None
