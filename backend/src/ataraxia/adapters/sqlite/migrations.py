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
    # 2: settings, lessons, jobs, Claude calls, reading sessions, and the activity record.
    # Subjects and event types are checked in code rather than here, because the
    # catalog and the record are expected to grow and a CHECK change means a rebuild.
    (
        """
        CREATE TABLE profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            time_zone TEXT NOT NULL,
            time_zone_confirmed INTEGER NOT NULL CHECK (time_zone_confirmed IN (0, 1)),
            subjects TEXT NOT NULL CHECK (json_valid(subjects)),
            lesson_length TEXT NOT NULL CHECK (lesson_length IN ('short', 'standard', 'long')),
            morning_lesson INTEGER NOT NULL CHECK (morning_lesson IN (0, 1)),
            morning_hour INTEGER NOT NULL CHECK (morning_hour BETWEEN 0 AND 23),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        ) STRICT
        """,
        """
        CREATE TABLE lessons (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            local_date TEXT NOT NULL,
            subject TEXT NOT NULL,
            origin TEXT NOT NULL
                CHECK (origin IN ('daily', 'surprise', 'subject', 'topic', 'follow_up')),
            request_text TEXT,
            parent_id TEXT REFERENCES lessons (id),
            thread_root_id TEXT NOT NULL REFERENCES lessons (id),
            part INTEGER NOT NULL CHECK (part >= 1),
            title TEXT NOT NULL,
            hook TEXT NOT NULL,
            reading_minutes INTEGER NOT NULL CHECK (reading_minutes > 0),
            body_markdown TEXT NOT NULL,
            key_ideas TEXT NOT NULL CHECK (json_valid(key_ideas)),
            glossary TEXT NOT NULL CHECK (json_valid(glossary)),
            go_deeper TEXT NOT NULL CHECK (json_valid(go_deeper)),
            further TEXT NOT NULL CHECK (json_valid(further)),
            illustrations TEXT NOT NULL CHECK (json_valid(illustrations)),
            tags TEXT NOT NULL CHECK (json_valid(tags)),
            model TEXT,
            prompt_version TEXT NOT NULL
        ) STRICT
        """,
        "CREATE INDEX lessons_newest ON lessons (created_at, id)",
        "CREATE INDEX lessons_thread ON lessons (thread_root_id, part)",
        """
        CREATE TABLE lesson_state (
            lesson_id TEXT PRIMARY KEY REFERENCES lessons (id),
            saved INTEGER NOT NULL DEFAULT 0 CHECK (saved IN (0, 1)),
            saved_at TEXT,
            rating INTEGER NOT NULL DEFAULT 0 CHECK (rating IN (-1, 0, 1)),
            rated_at TEXT,
            first_opened_at TEXT,
            finished_at TEXT,
            finished_on TEXT,
            read_seconds INTEGER NOT NULL DEFAULT 0 CHECK (read_seconds >= 0),
            furthest_scroll REAL NOT NULL DEFAULT 0 CHECK (furthest_scroll BETWEEN 0 AND 1),
            flagged_at TEXT,
            flag_note TEXT,
            CHECK ((finished_at IS NULL) = (finished_on IS NULL))
        ) STRICT
        """,
        """
        CREATE TABLE generation_jobs (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL
                CHECK (kind IN ('daily', 'surprise', 'subject', 'topic', 'follow_up')),
            status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
            local_date TEXT NOT NULL,
            subject TEXT,
            request_text TEXT,
            parent_lesson_id TEXT REFERENCES lessons (id),
            direction_index INTEGER CHECK (direction_index BETWEEN 0 AND 2),
            attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            error_code TEXT CHECK (error_code IN (
                'claude_auth', 'claude_usage_limit', 'claude_timeout', 'invalid_output',
                'claude_error', 'daily_limit', 'interrupted'
            )),
            lesson_id TEXT REFERENCES lessons (id),
            created_at TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            next_attempt_at TEXT,
            started_at TEXT,
            finished_at TEXT,
            CHECK ((kind = 'follow_up') = (parent_lesson_id IS NOT NULL)),
            CHECK ((status = 'succeeded') = (lesson_id IS NOT NULL))
        ) STRICT
        """,
        """
        CREATE UNIQUE INDEX generation_jobs_one_daily
            ON generation_jobs (local_date) WHERE kind = 'daily'
        """,
        "CREATE INDEX generation_jobs_by_status ON generation_jobs (status, created_at)",
        "CREATE INDEX generation_jobs_by_date ON generation_jobs (local_date)",
        """
        CREATE TABLE generation_calls (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES generation_jobs (id),
            local_date TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            outcome TEXT CHECK (outcome IN (
                'succeeded', 'claude_auth', 'claude_usage_limit', 'claude_timeout',
                'invalid_output', 'claude_error', 'daily_limit', 'interrupted'
            )),
            model TEXT,
            duration_ms INTEGER CHECK (duration_ms >= 0),
            input_tokens INTEGER CHECK (input_tokens >= 0),
            output_tokens INTEGER CHECK (output_tokens >= 0),
            cost_usd REAL CHECK (cost_usd >= 0)
        ) STRICT
        """,
        "CREATE INDEX generation_calls_by_date ON generation_calls (local_date)",
        "CREATE INDEX generation_calls_by_job ON generation_calls (job_id)",
        """
        CREATE TABLE reading_sessions (
            id TEXT PRIMARY KEY,
            lesson_id TEXT NOT NULL REFERENCES lessons (id),
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            local_date TEXT NOT NULL,
            seconds INTEGER NOT NULL CHECK (seconds >= 0),
            furthest_scroll REAL NOT NULL CHECK (furthest_scroll BETWEEN 0 AND 1)
        ) STRICT
        """,
        "CREATE INDEX reading_sessions_by_lesson ON reading_sessions (lesson_id)",
        "CREATE INDEX reading_sessions_by_date ON reading_sessions (local_date)",
        """
        CREATE TABLE activity_events (
            id INTEGER PRIMARY KEY,
            occurred_at TEXT NOT NULL,
            local_date TEXT NOT NULL,
            type TEXT NOT NULL,
            lesson_id TEXT REFERENCES lessons (id),
            subject TEXT,
            data TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(data))
        ) STRICT
        """,
        "CREATE INDEX activity_events_by_lesson ON activity_events (lesson_id)",
        "ALTER TABLE worker_status ADD COLUMN last_error_code TEXT",
        "ALTER TABLE worker_status ADD COLUMN last_error_at TEXT",
        "ALTER TABLE worker_status ADD COLUMN login_expires_at TEXT",
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
