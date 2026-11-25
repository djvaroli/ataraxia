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


def migrate(database: Database) -> int:
    """Bring the database to `SCHEMA_VERSION` and return the version found before.

    Safe to call from several processes at once: the version is read inside an
    immediate write transaction, so only one process applies each migration.
    Raises `UnsupportedSchemaError` instead of touching a newer schema.
    """
    database.path.parent.mkdir(parents=True, exist_ok=True)
    with database.connect() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
    with database.transaction() as connection:
        found = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if found > SCHEMA_VERSION:
            raise UnsupportedSchemaError(
                f"Database schema {found} is newer than supported {SCHEMA_VERSION}"
            )
        for statements in MIGRATIONS[found:]:
            for statement in statements:
                connection.execute(statement)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return found


def schema_version(database: Database) -> int:
    """Read the current schema version; used by readiness checks."""
    with database.connect() as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])
