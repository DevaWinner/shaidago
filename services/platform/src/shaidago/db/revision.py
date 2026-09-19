"""Migration head lookup and the readiness probe that compares it with the database."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from shaidago.shared.database import Database

ALEMBIC_INI = Path(__file__).parents[3] / "alembic.ini"


def alembic_config(url: str | None = None) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_INI.parent / "migrations"))
    if url is not None:
        config.attributes["url"] = url
    return config


def expected_head() -> str:
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    if head is None:
        raise RuntimeError("no migration revisions found")
    return head


class MigrationRevisionCheck:
    """Ready only when the database is exactly at the revision this build expects."""

    name = "migrations"
    required = True

    def __init__(self, database: Database, head: str) -> None:
        self._database = database
        self._head = head

    async def check(self) -> None:
        async with self._database.engine.connect() as connection:
            rows = (await connection.execute(text("SELECT version_num FROM alembic_version"))).all()
        if [row[0] for row in rows] != [self._head]:
            raise RuntimeError("database revision does not match this build")
