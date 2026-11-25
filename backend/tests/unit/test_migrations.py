"""Migrations run once, are safe to repeat, and refuse a newer schema."""

import sqlite3
from pathlib import Path

import pytest

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.migrations import (
    SCHEMA_VERSION,
    MigrationError,
    UnsupportedSchemaError,
    migrate,
    schema_version,
)

PARENT_AND_CHILD = (
    (
        "CREATE TABLE parent (id INTEGER PRIMARY KEY, name TEXT)",
        "CREATE TABLE child (id INTEGER PRIMARY KEY,"
        " parent_id INTEGER REFERENCES parent (id) ON DELETE CASCADE)",
        "INSERT INTO parent VALUES (1, 'a')",
        "INSERT INTO child VALUES (1, 1)",
    ),
)
REBUILD_PARENT = (
    "CREATE TABLE parent_new (id INTEGER PRIMARY KEY, name TEXT NOT NULL)",
    "INSERT INTO parent_new SELECT id, name FROM parent",
    "DROP TABLE parent",
    "ALTER TABLE parent_new RENAME TO parent",
)


def test_migrate_creates_schema_and_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "nested" / "app.db")
    assert migrate(database) == 0
    assert migrate(database) == SCHEMA_VERSION
    assert schema_version(database) == SCHEMA_VERSION
    with database.connect() as connection:
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


def test_newer_schema_is_refused(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    migrate(database)
    with database.connect() as connection:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    with pytest.raises(UnsupportedSchemaError):
        migrate(database)


def test_failed_transaction_rolls_back(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    migrate(database)
    with pytest.raises(RuntimeError), database.transaction() as connection:
        connection.execute("INSERT INTO worker_status (id, heartbeat_at) VALUES (1, 'x')")
        raise RuntimeError("abort")
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM worker_status").fetchone()[0] == 0


def test_table_rebuild_keeps_child_rows(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    migrate(database, PARENT_AND_CHILD)
    migrate(database, (*PARENT_AND_CHILD, REBUILD_PARENT))
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM child").fetchone()[0] == 1


def test_foreign_key_violation_rolls_back_the_migration(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    migrate(database, PARENT_AND_CHILD)
    orphan = ("INSERT INTO child VALUES (2, 99)",)
    with pytest.raises(MigrationError):
        migrate(database, (*PARENT_AND_CHILD, orphan))
    assert schema_version(database) == 1
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM child").fetchone()[0] == 1


def test_rollback_keeps_the_original_error(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    migrate(database, PARENT_AND_CHILD)
    with pytest.raises(sqlite3.IntegrityError), database.transaction() as connection:
        connection.execute("INSERT OR ROLLBACK INTO parent VALUES (1, 'duplicate')")
