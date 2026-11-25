"""The append-only activity record."""

from ataraxia.adapters.sqlite import rows
from ataraxia.adapters.sqlite.database import Database
from ataraxia.application.views import ActivityEvent
from ataraxia.domain.activity import NewEvent


class ActivityRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def append(self, event: NewEvent) -> None:
        with self._database.transaction() as connection:
            rows.insert_event(connection, event)

    def page(self, after_id: int | None, limit: int) -> list[ActivityEvent]:
        """Events in the order they were written, after `after_id`."""
        with self._database.connect() as connection:
            found = connection.execute(
                "SELECT * FROM activity_events WHERE id > ? ORDER BY id LIMIT ?",
                (after_id or 0, limit),
            ).fetchall()
        return [rows.activity_event(row) for row in found]

    def all_events(self) -> list[ActivityEvent]:
        with self._database.connect() as connection:
            found = connection.execute("SELECT * FROM activity_events ORDER BY id").fetchall()
        return [rows.activity_event(row) for row in found]
