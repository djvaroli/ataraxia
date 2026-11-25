"""Export, summarize, or back up the Ataraxia database.

Run inside the API container, for example:

    docker compose exec api python -m ataraxia.tools stats

Exit codes: 0 success, 1 failure (message on stderr), 2 usage error.
"""

import argparse
import os
import sqlite3
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.migrations import SCHEMA_VERSION, schema_version
from ataraxia.application.progress import ProgressService
from ataraxia.application.records import ExportService
from ataraxia.bootstrap import ConfigurationError, create_tools
from ataraxia.config import Settings
from ataraxia.domain.subjects import subject

STATS_DAYS = 14


class ToolError(Exception):
    """A failure to report in one line, without a traceback."""


def check_database(database: Database) -> None:
    """Refuse a missing file or a schema this version does not match, rather than
    creating or migrating a database from a read-only tool."""
    if not database.path.is_file():
        raise ToolError(f"No database at {database.path}")
    try:
        found = schema_version(database)
    except sqlite3.Error as error:
        raise ToolError(f"Cannot read {database.path}: {error}") from error
    if found != SCHEMA_VERSION:
        raise ToolError(f"Database schema is {found}; this tool expects {SCHEMA_VERSION}")


def export(service: ExportService, output: Path | None, stdout: TextIO) -> None:
    """Write the complete JSON export to `output` (replaced atomically) or stdout."""
    document = service.export().model_dump_json(indent=2) + "\n"
    if output is None:
        stdout.write(document)
        return
    with tempfile.NamedTemporaryFile(
        "w", dir=output.parent, prefix=f".{output.name}.", delete=False, encoding="utf-8"
    ) as temporary:
        temporary.write(document)
    os.replace(temporary.name, output)


def stats(service: ProgressService, stdout: TextIO) -> None:
    """Plain-text totals by subject and the last two weeks."""
    progress = service.progress(days=STATS_DAYS)
    lines = [
        f"Lessons {progress.lessons_total}, finished {progress.finished_total}, "
        f"saved {progress.saved_total}, minutes read {progress.read_minutes_total}",
        f"Streak {progress.current_streak} days (longest {progress.longest_streak})",
        "",
        f"{'Subject':<26}{'Lessons':>8}{'Finished':>10}{'Minutes':>9}{'Liked':>7}{'Disliked':>10}",
    ]
    for row in progress.subjects:
        lines.append(
            f"{subject(row.subject).label:<26}{row.lessons:>8}{row.finished:>10}"
            f"{row.read_minutes:>9}{row.liked:>7}{row.disliked:>10}"
        )
    lines += ["", f"{'Date':<12}{'Finished':>10}{'Minutes':>9}"]
    for day in progress.days:
        lines.append(f"{day.date.isoformat():<12}{day.finished:>10}{day.read_minutes:>9}")
    stdout.write("\n".join(lines) + "\n")


def backup(database: Database, target: Path) -> None:
    """Copy the database with SQLite's online backup into a new file.

    The copy is written beside the target and linked into place, so `target` is
    either absent or complete, and an existing file is never replaced.
    """
    if target.exists():
        raise ToolError(f"{target} already exists; choose a new name")
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, partial_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    os.close(handle)
    partial = Path(partial_name)
    try:
        with database.connect() as source:
            copy = sqlite3.connect(partial)
            try:
                source.backup(copy)
                # A single self-contained file, whatever the source's journal mode.
                copy.execute("PRAGMA journal_mode = DELETE")
            finally:
                copy.close()
        try:
            os.link(partial, target)
        except FileExistsError as error:
            raise ToolError(f"{target} already exists; choose a new name") from error
    finally:
        partial.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ataraxia.tools",
        description="Read or copy the Ataraxia database named by ATARAXIA_DATABASE_PATH.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser(
        "export", help="write every durable record as versioned JSON"
    )
    export_parser.add_argument(
        "--output", type=Path, help="file to write (replaced if present); default stdout"
    )
    commands.add_parser("stats", help=f"print totals by subject and the last {STATS_DAYS} days")
    backup_parser = commands.add_parser(
        "backup", help="copy the database to a new file with SQLite's online backup"
    )
    backup_parser.add_argument("path", type=Path, help="new file to create; never overwritten")
    return parser


def main(argv: Sequence[str] | None = None, stdout: TextIO = sys.stdout) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        services = create_tools(Settings())
        check_database(services.database)
        if arguments.command == "export":
            export(services.export, arguments.output, stdout)
        elif arguments.command == "stats":
            stats(services.progress, stdout)
        else:
            backup(services.database, arguments.path)
            print(f"Backed up to {arguments.path}", file=sys.stderr)
    except (ToolError, ConfigurationError, OSError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
