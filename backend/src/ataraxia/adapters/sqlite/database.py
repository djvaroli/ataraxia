"""Short-lived SQLite connections with the settings every process must share."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

BUSY_TIMEOUT_MS = 5000


class Database:
    """One SQLite file shared by the API and worker processes on the same host.

    Each operation opens its own connection, which keeps threads and processes
    independent. WAL mode (set by migrations) lets readers proceed during a write;
    the busy timeout bounds how long a writer waits for another process.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self, *, foreign_keys: bool = True) -> Iterator[sqlite3.Connection]:
        """Open a connection in autocommit mode; callers use `transaction` for writes.

        Only migrations turn `foreign_keys` off, so that rebuilding a table cannot
        cascade deletes; the pragma has no effect once a transaction has begun.
        """
        connection = sqlite3.connect(
            self.path, timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute(f"PRAGMA foreign_keys = {'ON' if foreign_keys else 'OFF'}")
            connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self, *, foreign_keys: bool = True) -> Iterator[sqlite3.Connection]:
        """Run statements in one write transaction, rolling back on any error.

        `BEGIN IMMEDIATE` takes the write lock up front, so a read-then-write
        sequence inside the block cannot interleave with another writer.
        """
        with self.connect(foreign_keys=foreign_keys) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                # SQLite may already have rolled back (disk full, I/O error); a second
                # ROLLBACK would raise and hide the original error.
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")
