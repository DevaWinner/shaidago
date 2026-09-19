"""Mapping options for tables written by the restricted submission role (ADR-0003).

The public role may INSERT into private tables but cannot SELECT from them, and PostgreSQL needs
SELECT privilege for ``INSERT ... RETURNING``. A mapped class for such a table therefore must:

* use ``PRIVATE_TABLE_ARGS`` (``implicit_returning=False``) and ``PRIVATE_MAPPER_ARGS``
  (``eager_defaults=False``);
* generate its primary key (UUIDv7) and timestamps in the application, and declare no
  ``server_default`` the ORM would want to read back;
* be added with ``session.add(...)`` and ``flush()``, never refreshed.
"""

from typing import Any, Final

PRIVATE_TABLE_ARGS: Final[dict[str, Any]] = {"schema": "app", "implicit_returning": False}
PRIVATE_MAPPER_ARGS: Final[dict[str, Any]] = {"eager_defaults": False}
