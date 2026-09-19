"""The single SQLAlchemy metadata registry that Alembic and every mapped table share.

Importing this module never imports the running application. Constraint and index names follow
one convention so migrations, reviews, and error handling can refer to them by stable name.
Table modules import ``Base`` from here; ``migrations/env.py`` imports each table module so its
tables register before autogenerate comparison.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata


# Alembic cannot compare partial or expression indexes, so autogenerate skips these by name.
# `tests/integration/test_migrations.py` asserts their exact definitions from `pg_indexes`.
UNCOMPARABLE_INDEXES = frozenset({"ix_projects_public_recent", "ix_project_translations_search"})


def include_object(
    _object: object, name: str | None, type_: str, _reflected: bool, _compare_to: object
) -> bool:
    """Filter for Alembic comparison: skip the version table and the uncomparable indexes."""
    if type_ == "table" and name == "alembic_version":
        return False
    return not (type_ == "index" and name in UNCOMPARABLE_INDEXES)
