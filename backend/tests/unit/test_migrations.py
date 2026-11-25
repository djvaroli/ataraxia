"""Migrations run once, are safe to repeat, and refuse a newer schema."""

from pathlib import Path

import pytest

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.migrations import (
    SCHEMA_VERSION,
    UnsupportedSchemaError,
    migrate,
    schema_version,
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
