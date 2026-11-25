"""Numbered schema migrations tracked with `PRAGMA user_version`.

Migrations are append-only once merged: change the schema by adding a new entry,
never by editing an old one. Each entry is a sequence of single statements so the
whole upgrade runs in one transaction (`executescript` would commit early).
"""

from collections.abc import Sequence

from ataraxia.adapters.sqlite.database import Database

MIGRATIONS: Sequence[Sequence[str]] = (
    # 1: worker heartbeat, so the API can tell whether lessons can be prepared.
    (
        """
        CREATE TABLE worker_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            heartbeat_at TEXT NOT NULL
        ) STRICT
        """,
    ),
)

SCHEMA_VERSION = len(MIGRATIONS)


class UnsupportedSchemaError(RuntimeError):
    """The database was written by a newer version of the application."""


class MigrationError(RuntimeError):
    """A migration left rows that violate a foreign key; nothing was committed."""


def migrate(database: Database, migrations: Sequence[Sequence[str]] = MIGRATIONS) -> int:
    """Bring the database to the latest version and return the version found before.

    Safe to call from several processes at once: the version is read inside an
    immediate write transaction, so only one process applies each migration.
    Foreign keys are off while migrating (so a table rebuild cannot cascade
    deletes) and checked before commit. Raises `UnsupportedSchemaError` instead of
    touching a newer schema.
    """
    target = len(migrations)
    database.path.parent.mkdir(parents=True, exist_ok=True)
    with database.connect() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
    with database.transaction(foreign_keys=False) as connection:
        found = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if found > target:
            raise UnsupportedSchemaError(
                f"Database schema {found} is newer than supported {target}"
            )
        for statements in migrations[found:]:
            for statement in statements:
                connection.execute(statement)
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise MigrationError("Migration left rows that violate a foreign key")
        connection.execute(f"PRAGMA user_version = {target}")
    return found


def schema_version(database: Database) -> int:
    """Read the current schema version; used by readiness checks."""
    with database.connect() as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])
